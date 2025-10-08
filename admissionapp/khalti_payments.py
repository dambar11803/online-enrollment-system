# views_payments.py
import json
import uuid
from decimal import Decimal, ROUND_DOWN 
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test
)
from django.db import transaction
import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt 
from .models import Application, PaymentDetail 
from django.http import JsonResponse, HttpResponseBadRequest 
from .models import Notification 


#Helper Function 
def create_notification(user, title, message):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )
    return notification

# -----------------------------
# Khalti Integration
# -----------------------------
KHALTI_HEADERS = {
    "Authorization": f"Key {settings.KHALTI_SECRET_KEY.strip()}",
    "Content-Type": "application/json",
}


@login_required
def khalti_initiate(request, application_id):
    app = get_object_or_404(
        Application,
        pk=application_id,
        user=request.user
    )
    course = app.course  # FK to CourseDetails 
    
    # Check if already paid
    if app.is_paid:
        messages.info(request, "Payment is already completed for this application.")
        return redirect("student_dashboard")

    # Amount in paisa 
    course_full_fee = 50
    course_full_fee = course_full_fee * 100
    course_full_fee = int(course_full_fee)
    amount_paisa = course_full_fee

    purchase_order_id = f"APP-{app.pk}-{uuid.uuid4().hex[:6]}"
    purchase_order_name = course.course_name

    payload = {
        "return_url": request.build_absolute_uri(
            "/pay/khalti/return/"
        ),
        "website_url": request.build_absolute_uri("/"),
        "amount": amount_paisa,
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": purchase_order_name,
        "customer_info": {
            "name": (
                request.user.get_full_name() or
                request.user.username
            ),
            "email": request.user.email or "dev@example.com",
        },
        "product_details": [
            {
                "identity": course.course_code or str(course.pk),
                "name": course.course_name,
                "total_price": amount_paisa,
                "quantity": 1,
                "unit_price": amount_paisa,
            }
        ],
        "merchant_application_id": str(app.pk),
        "merchant_course_id": str(course.pk),
        "merchant_user_id": str(request.user.pk),
    }

    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    r = requests.post(
        settings.KHALTI_INITIATE_URL,
        json=payload,
        headers=headers,
        timeout=20
    )
    data = r.json()
    if r.status_code != 200 or "payment_url" not in data:
        return HttpResponseBadRequest(
            f"Initiation failed: {r.status_code} {data}"
        )

    # Save/remember what you'll need after return
    request.session.update(
        {
            "khalti_pidx": data.get("pidx"),
            "khalti_order_id": purchase_order_id,
            "khalti_course_name": course.course_name,
            "khalti_amount_paisa": amount_paisa,
            "khalti_application_id": app.pk,
        }
    )
    return redirect(data["payment_url"])



@csrf_exempt
def khalti_return(request):
    # --- 1) Collect identifiers from GET (fallbacks to session) ---
    pidx = request.GET.get("pidx") or request.session.get("khalti_pidx")
    if not pidx:
        return HttpResponseBadRequest("Missing pidx")

    purchase_order_id = request.GET.get("purchase_order_id")
    merchant_app_id = request.GET.get("merchant_application_id")
    txn_id = (
        request.GET.get("transaction_id")
        or request.GET.get("txnId")
        or request.GET.get("tidx")
    )

    # --- 2) Verify with Khalti (server-to-server) ---
    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    r = requests.post(
        settings.KHALTI_LOOKUP_URL,
        json={"pidx": pidx},
        headers=headers,
        timeout=20
    )
    data = r.json()

    # --- 3) Choose status & amount from verified response (fallback to GET) ---
    ext_status = (data.get("status") or request.GET.get("status") or "").upper()
    amount_paisa = data.get("total_amount") or request.GET.get("total_amount") or request.GET.get("amount") or 0
    try:
        amount_paisa = int(amount_paisa)
    except (TypeError, ValueError):
        amount_paisa = 0
    amount_rs = (Decimal(amount_paisa) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # --- 4) Resolve Application id robustly ---
    app_id = None
    if merchant_app_id:
        try:
            app_id = int(merchant_app_id)
        except ValueError:
            app_id = None
    if app_id is None and purchase_order_id and purchase_order_id.startswith("APP-"):
        parts = purchase_order_id.split("-")
        if len(parts) >= 2:
            try:
                app_id = int(parts[1])
            except ValueError:
                pass
    if app_id is None:
        app_id = request.session.get("khalti_application_id")

    # Build context for template
    ctx = {
        "order_id": purchase_order_id or request.session.get("khalti_order_id"),
        "course_name": request.session.get("khalti_course_name"),
        "amount_rs": amount_rs,
        "resp": data,
        "pidx": pidx,
    }

    # Map external → internal
    status_map = {
        "COMPLETED": "COMPLETE",
        "PENDING": "PENDING",
        "USER_CANCELLED": "CANCELED",
        "CANCELLED": "CANCELED",
        "CANCELED": "CANCELED",
        "FAILED": "FAILED",
    }
    internal_status = status_map.get(ext_status, "FAILED")

    # --- 5) Write DB state atomically ---
    if app_id:
        try:
            with transaction.atomic():
                app = Application.objects.select_for_update().get(pk=app_id)

                # Successful payment → upsert PaymentDetail and mark app paid
                if r.status_code == 200 and ext_status == "COMPLETED":
                    defaults = {
                        "user": getattr(request, "user", None) if request.user.is_authenticated else app.user,
                        "amount_paid": amount_rs,
                        "is_payment_completed": True,
                        "transaction_uuid": pidx,     # stable id in your system
                        "product_code": "KHALTI",
                        "status": "COMPLETE",
                        "payment_method": "Khalti",
                    }

                    try:
                        pd = app.payment  # OneToOne via related_name="payment"
                        if pd.status != "COMPLETE":
                            for k, v in defaults.items():
                                setattr(pd, k, v)
                            # Optional: if you add a gateway_txn_id field later
                            if hasattr(pd, "gateway_txn_id") and txn_id:
                                pd.gateway_txn_id = txn_id
                            pd.save()
                    except PaymentDetail.DoesNotExist:
                        pd_kwargs = {"application": app, **defaults}
                        if hasattr(PaymentDetail, "gateway_txn_id") and txn_id:
                            pd_kwargs["gateway_txn_id"] = txn_id
                        PaymentDetail.objects.create(**pd_kwargs)

                    if hasattr(app, "is_paid") and not app.is_paid:
                        app.is_paid = True
                        app.save(update_fields=["is_paid"])

                    # Create notification
                    create_notification(
                        user=request.user,
                        title="Payment with Khalti",
                        message="Your payment has been done successfully and saved.",
                    )

                # Non-complete → upsert a record for audit but don't mark paid
                else:
                    try:
                        pd = app.payment
                        if pd.status != "COMPLETE":
                            pd.status = internal_status
                            pd.payment_method = "Khalti"
                            pd.transaction_uuid = pd.transaction_uuid or pidx
                            pd.amount_paid = amount_rs
                            if hasattr(pd, "gateway_txn_id") and txn_id:
                                pd.gateway_txn_id = txn_id
                            pd.save()
                    except PaymentDetail.DoesNotExist:
                        PaymentDetail.objects.create(
                            application=app,
                            user=(request.user if request.user.is_authenticated else app.user),
                            amount_paid=amount_rs,
                            is_payment_completed=False,
                            transaction_uuid=pidx,
                            product_code="KHALTI",
                            status=internal_status,
                            payment_method="Khalti",
                        )
        except Application.DoesNotExist:
            # Can't resolve Application → show failed page
            return render(request, "payments/failed.html", ctx)

    # --- 6) Clear session noise (optional) ---
    for k in ("khalti_pidx", "khalti_order_id", "khalti_course_name", "khalti_amount_paisa", "khalti_application_id"):
        request.session.pop(k, None)

    # --- 7) Render final page ---
    if r.status_code == 200 and ext_status == "COMPLETED":
        return render(request, "payments/success.html", ctx)
    return render(request, "payments/failed.html", ctx)



@login_required
def khalti_verify(request):
    """Optional endpoint to re-verify a pidx later (AJAX)."""
    pidx = request.GET.get("pidx")
    if not pidx:
        return HttpResponseBadRequest("Missing pidx")
    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    r = requests.post(
        settings.KHALTI_LOOKUP_URL,
        json={"pidx": pidx},
        headers=headers,
        timeout=20
    )
    return JsonResponse(r.json(), status=r.status_code) 
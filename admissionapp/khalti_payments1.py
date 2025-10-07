# views_payments.py
import json
import uuid
from decimal import Decimal, ROUND_DOWN 
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test
)

import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt 
from .models import Application, PaymentDetail

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
    # 1) Get pidx from query or session
    pidx = request.GET.get("pidx") or request.session.get(
        "khalti_pidx"
    )
    if not pidx:
        return HttpResponseBadRequest("Missing pidx")

    # 2) Verify with Khalti (lookup)
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

    # 3) Build the template context
    amount_paisa = (
        data.get("total_amount") or
        request.session.get("khalti_amount_paisa")
    )
    try:
        amount_paisa = int(amount_paisa)
    except (TypeError, ValueError):
        amount_paisa = 0

    ctx = {
        "order_id": (
            request.session.get("khalti_order_id") or
            request.GET.get("purchase_order_id")
        ),
        "course_name": request.session.get("khalti_course_name"),
        "amount_rs": amount_paisa / 100,  # convert paisa -> NPR
        "resp": data,
        "pidx": pidx,
    }

    # 4) Render success/failed
    if r.status_code == 200 and data.get("status") == "Completed":
        # (optional) clear session keys so they aren't reused
        for k in (
            "khalti_pidx",
            "khalti_order_id",
            "khalti_course_name",
            "khalti_amount_paisa",
        ):
            request.session.pop(k, None)
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
# views_payments.py
import base64
import hashlib
import hmac
import json
import uuid
from collections import OrderedDict
from decimal import Decimal, ROUND_DOWN

import requests
from django.conf import settings
from django.contrib import messages
from django.db import transaction as db_transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .models import Application, PaymentDetail, Notification


#Helper Function 

def create_notification(user, title, message):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )
    return notification

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _fmt_amount_for_esewa(amount) -> str:
    """
    Format amount to always have 2 decimal places.
    Example: 1000 -> "1000.00", 1234.5 -> "1234.50"
    """
    amt = Decimal(str(amount or 0)).quantize(Decimal("0.00"), rounding=ROUND_DOWN)
    return f"{amt:.2f}"


def _generate_esewa_signature(total_amount: str, transaction_uuid: str, product_code: str) -> str:
    """
    Generate eSewa payment signature using HMAC SHA256.
    
    Args:
        total_amount: Amount in format "1000.00"
        transaction_uuid: Unique transaction ID
        product_code: eSewa product code (EPAYTEST for test, NP-ES-XXX for production)
    
    Returns:
        Base64 encoded signature string
    """
    # Create message in exact format: total_amount=X,transaction_uuid=Y,product_code=Z
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    
    # Get secret key from settings
    secret_key = settings.ESEWA_SECRET_KEY.strip()
    
    # Generate HMAC SHA256
    hmac_digest = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Encode to base64
    signature = base64.b64encode(hmac_digest).decode('utf-8')
    
    # Debug logging (remove in production)
    print(f"\n{'='*60}")
    print(f"eSewa Signature Generation Debug:")
    print(f"{'='*60}")
    print(f"Message: {message}")
    print(f"Secret Key Length: {len(secret_key)}")
    print(f"Signature: {signature}")
    print(f"{'='*60}\n")
    
    return signature


# ============================================================================
# PAYMENT INITIATION VIEW
# ============================================================================

def esewa_initiate(request, application_id):
    """
    Initiate eSewa payment for an application.
    Creates PaymentDetail record and renders payment form.
    """
    # Get application for logged-in user
    application = get_object_or_404(Application, pk=application_id, user=request.user)

    # Check if already paid
    if getattr(application, "is_paid", False):
        messages.info(request, "Payment is already completed for this application.")
        return redirect("student_dashboard")

    # Get course fee and format as string with 2 decimal places
    # course_fee = getattr(application.course, "course_fee", 0)
    course_fee = 50.00
    total_amount_str = _fmt_amount_for_esewa(course_fee)

    # Get or create payment record
    payment, created = PaymentDetail.objects.get_or_create(
        application=application,
        defaults={
            "user": request.user,
            "amount_paid": Decimal(total_amount_str),
            "transaction_uuid": uuid.uuid4().hex,
            "product_code": settings.ESEWA_PRODUCT_CODE.strip(),
            "status": "INITIATED",
            "payment_method": "e-Sewa",
        },
    )

    # If payment record already exists, update it for retry
    if not created:
        if payment.is_payment_completed:
            messages.info(request, "Payment is already completed for this application.")
            return redirect("student_dashboard")
        
        # Reset for new payment attempt
        payment.amount_paid = Decimal(total_amount_str)
        payment.transaction_uuid = uuid.uuid4().hex
        payment.product_code = settings.ESEWA_PRODUCT_CODE.strip()
        payment.status = "INITIATED"
        payment.payment_method = "e-Sewa"
        payment.save(
            update_fields=[
                "amount_paid", "transaction_uuid", "product_code", 
                "status", "payment_method", "updated_at"
            ]
        )

    # Generate signature for these exact 3 fields
    signature = _generate_esewa_signature(
        total_amount=total_amount_str,
        transaction_uuid=payment.transaction_uuid,
        product_code=payment.product_code
    )

    # Prepare context for template
    context = {
        # eSewa form URL
        "esewa_form_url": settings.ESEWA_FORM_URL.strip(),
        
        # Callback URLs
        "success_url": request.build_absolute_uri(reverse("esewa_success")),
        "failure_url": request.build_absolute_uri(reverse("esewa_failure")),
        
        # Signed fields (these 3 fields are used in signature)
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
        
        # Payment details (must match signed values exactly)
        "total_amount": total_amount_str,
        "transaction_uuid": payment.transaction_uuid,
        "product_code": payment.product_code,
        
        # Additional fields (not signed but required by eSewa)
        "amount": total_amount_str,
        "tax_amount": "0",
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        
        # Payment object for template reference
        "payment": payment,
        "application": application,
    }

    return render(request, "payments/esewa_initiate.html", context)


# ============================================================================
# SUCCESS CALLBACK VIEW
# ============================================================================

@csrf_exempt
def esewa_success(request):
    """
    eSewa success callback endpoint.
    Receives base64-encoded payment data, verifies with eSewa, and updates payment status.
    """
    if request.method != "GET":
        return HttpResponse("Method not allowed", status=405)

    # Get base64 encoded data from query parameter
    data = request.GET.get("data")
    if not data:
        messages.error(request, "Invalid payment response from eSewa.")
        return redirect("student_dashboard")

    # Decode and parse JSON data
    try:
        decoded = base64.b64decode(data).decode("utf-8")
        payload = json.loads(decoded)
    except Exception as e:
        print(f"Error decoding eSewa response: {e}")
        messages.error(request, "Invalid payment data format.")
        return redirect("student_dashboard")

    # Extract transaction details
    transaction_uuid = payload.get("transaction_uuid")
    transaction_code = payload.get("transaction_code")  # eSewa reference number

    if not transaction_uuid:
        messages.error(request, "Invalid transaction data.")
        return redirect("student_dashboard")

    # Process payment verification atomically
    with db_transaction.atomic():
        try:
            # Lock payment record to prevent concurrent updates
            payment = PaymentDetail.objects.select_for_update().get(
                transaction_uuid=transaction_uuid
            )
        except PaymentDetail.DoesNotExist:
            messages.error(request, "Payment record not found.")
            return redirect("student_dashboard")

        # Check if already processed (idempotent)
        if payment.is_payment_completed:
            messages.success(request, "Payment already verified.")
            return redirect("student_dashboard")

        # Prepare verification request to eSewa
        total_amount_str = _fmt_amount_for_esewa(payment.amount_paid)
        verification_url = (
            f"{settings.ESEWA_STATUS_URL}"
            f"?product_code={payment.product_code}"
            f"&total_amount={total_amount_str}"
            f"&transaction_uuid={payment.transaction_uuid}"
        )

        print(f"\nVerifying payment with eSewa:")
        print(f"URL: {verification_url}")

        # Make verification request to eSewa
        try:
            resp = requests.get(verification_url, timeout=10)
        except requests.RequestException as e:
            print(f"Error connecting to eSewa: {e}")
            payment.status = "VERIFICATION_ERROR"
            payment.save(update_fields=["status", "updated_at"])
            messages.error(request, "Unable to verify payment. Please contact support.")
            return redirect("student_dashboard")

        # Check response status
        if resp.status_code != 200:
            print(f"eSewa returned status code: {resp.status_code}")
            payment.status = "VERIFICATION_ERROR"
            payment.save(update_fields=["status", "updated_at"])
            messages.error(request, "Unable to verify payment. Please contact support.")
            return redirect("student_dashboard")

        # Parse verification response
        try:
            verification_data = resp.json() if resp.content else {}
        except Exception as e:
            print(f"Error parsing eSewa response: {e}")
            verification_data = {}

        # Get status and amount from verification response
        v_status = verification_data.get("status")
        v_amount = _fmt_amount_for_esewa(verification_data.get("total_amount", 0))

        print(f"Verification response:")
        print(f"Status: {v_status}")
        print(f"Amount: {v_amount}")
        print(f"Expected amount: {total_amount_str}")

        # Verify payment completion
        if v_status == "COMPLETE" and v_amount == total_amount_str:
            # Update payment record
            payment.transaction_reference = transaction_code or payment.transaction_reference
            payment.status = "COMPLETE"
            payment.is_payment_completed = True
            payment.save(
                update_fields=[
                    "transaction_reference", "status", 
                    "is_payment_completed", "updated_at"
                ]
            )

            # Mark application as paid
            application = payment.application
            if hasattr(application, "is_paid"):
                application.is_paid = True
                application.save(update_fields=["is_paid"])
            
            # Create notification
            create_notification(
                user=request.user,
                title="Pay with E-Sewa",
                message="Your payment has been done successfully and saved.",
            )    
                

            messages.success(request, "Payment completed successfully via eSewa!")
            return redirect("student_dashboard")
        else:
            # Verification failed
            payment.status = "VERIFICATION_FAILED"
            payment.save(update_fields=["status", "updated_at"])
            messages.error(
                request, 
                "Payment verification failed. Please contact support with your transaction reference."
            )
            return redirect("student_dashboard")


# ============================================================================
# FAILURE CALLBACK VIEW
# ============================================================================

@csrf_exempt
def esewa_failure(request):
    """
    eSewa failure/cancel callback endpoint.
    Updates payment status when user cancels or payment fails.
    """
    data = request.GET.get("data")
    transaction_uuid = None

    # Try to extract transaction UUID if data provided
    if data:
        try:
            decoded = base64.b64decode(data).decode("utf-8")
            payload = json.loads(decoded)
            transaction_uuid = payload.get("transaction_uuid")
        except Exception as e:
            print(f"Error decoding failure data: {e}")
            transaction_uuid = None

    # Update payment status if we found the transaction
    if transaction_uuid:
        try:
            payment = PaymentDetail.objects.get(transaction_uuid=transaction_uuid)
            payment.status = "FAILED"
            payment.is_payment_completed = False
            payment.save(
                update_fields=["status", "is_payment_completed", "updated_at"]
            )
            messages.error(request, "Payment failed or was canceled. Please try again.")
        except PaymentDetail.DoesNotExist:
            messages.error(request, "Invalid transaction reference.")
    else:
        messages.error(request, "Payment was not completed.")

    return redirect("student_dashboard")
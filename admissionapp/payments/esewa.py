# admissionapp/payments/esewa.py
import hmac, hashlib, base64

def esewa_signature(secret_key: str, *, total_amount: str, transaction_uuid: str, product_code: str) -> str:
    # Exactly this order & CSV of "key=value"
    payload = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    digest = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

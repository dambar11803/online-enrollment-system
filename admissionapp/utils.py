# payments/utils.py
import base64, hmac, hashlib

def esewa_signature(secret_key: str, total_amount: str, transaction_uuid: str, product_code: str) -> str:
    """
    HMAC-SHA256 over: total_amount,transaction_uuid,product_code  (in that exact order)
    Return Base64-encoded signature (UTF-8).
    """
    message = f"total_amount={total_amount} and transaction_uuid={transaction_uuid}"
    dig = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(dig).decode("utf-8")

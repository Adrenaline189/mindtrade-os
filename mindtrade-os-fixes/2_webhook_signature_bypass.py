"""
FIX 2: bot/license_service.py - Webhook signature verification must NOT bypass when secret is empty

REPLACE the verify_binancepay_signature function (near the end of file) with this:

def verify_binancepay_signature(payload_bytes: bytes, signature: str | None, secret: str) -> bool:
    if not secret:
        # Security fix: If secret is not configured, REJECT all webhooks.
        # Admin MUST set BINANCE_PAY_WEBHOOK_SECRET in production.
        raise ValueError(
            "BINANCE_PAY_WEBHOOK_SECRET is not configured. "
            "Webhook verification is disabled — this is insecure for production."
        )
    got = (signature or '').strip().lower()
    if not got:
        return False
    digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest().lower()
    return hmac.compare_digest(digest, got)
"""

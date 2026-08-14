import hashlib
import hmac
from typing import Optional


def verify_github_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    secret: Optional[str],
) -> bool:
    """
    Verifies GitHub webhook HMAC-SHA256 signature in constant time.
    Format: 'sha256=<hex_digest>'
    """
    if not signature_header or not secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]
    computed_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)

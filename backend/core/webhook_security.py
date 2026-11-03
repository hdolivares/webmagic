"""
Authentication for inbound SMS provider webhooks.

Both verifiers fail closed: if the relevant secret is not configured,
every request is rejected rather than silently accepted.
"""
import base64
import binascii
import hmac
import logging
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, Query, Request, status

from core.config import get_settings

logger = logging.getLogger(__name__)

TELNYX_TIMESTAMP_TOLERANCE_SECONDS = 300


async def verify_labsmobile_token(token: str = Query("", include_in_schema=False)) -> None:
    """
    LabsMobile does not sign its callbacks, so callback URLs carry a shared
    secret (``?token=...``) that we compare in constant time.
    """
    expected = get_settings().LABSMOBILE_WEBHOOK_TOKEN
    if not expected:
        logger.error("LABSMOBILE_WEBHOOK_TOKEN is not configured; rejecting webhook")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def verify_telnyx_signature(request: Request) -> None:
    """
    Verify Telnyx's Ed25519 webhook signature over ``{timestamp}|{raw body}``.
    """
    public_key_b64 = get_settings().TELNYX_PUBLIC_KEY
    signature_b64 = request.headers.get("telnyx-signature-ed25519")
    timestamp = request.headers.get("telnyx-timestamp")

    if not public_key_b64:
        logger.error("TELNYX_PUBLIC_KEY is not configured; rejecting webhook")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not signature_b64 or not timestamp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    try:
        if abs(time.time() - int(timestamp)) > TELNYX_TIMESTAMP_TOLERANCE_SECONDS:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale webhook")
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        body = await request.body()  # Starlette caches this for the handler
        public_key.verify(base64.b64decode(signature_b64), f"{timestamp}|".encode() + body)
    except (ValueError, binascii.Error, InvalidSignature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

"""
Security regression tests: auth boundaries, webhook verification, and input hardening.

These run against the real FastAPI app with no database; every request here is
rejected (or answered) before a database connection is needed.
"""
import base64
import hashlib
import hmac
import time
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.v1.campaigns import _is_allowed_redirect
from core.config import Settings, get_settings
from core.customer_security import create_customer_access_token
from core.security import create_access_token, verify_token
from services.payments.recurrente_client import RecurrenteClient
from services.platform.nginx_provisioning import _is_safe_hostname
from services.validation.url_prescreener import URLPrescreener

client = TestClient(app, raise_server_exceptions=False)
API_PATHS = set(app.openapi()["paths"])


def _svix_headers(body: str, secret: bytes = b"k" * 24, timestamp: int | None = None) -> dict:
    msg_id, ts = "msg_test", str(timestamp or int(time.time()))
    digest = hmac.new(secret, f"{msg_id}.{ts}.{body}".encode(), hashlib.sha256).digest()
    return {"svix-id": msg_id, "svix-timestamp": ts, "svix-signature": f"v1,{base64.b64encode(digest).decode()}"}


# ── Configuration ─────────────────────────────────────────────────────────────

def test_weak_secret_key_is_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="your-secret-key-here")


def test_api_docs_disabled_outside_debug():
    assert app.docs_url is None and app.redoc_url is None and app.openapi_url is None


def test_cors_allows_only_configured_origins():
    preflight = {"Access-Control-Request-Method": "POST"}
    evil = client.options("/api/v1/auth/login", headers={"Origin": "https://evil.example", **preflight})
    ours = client.options("/api/v1/auth/login", headers={"Origin": "https://app.example.com", **preflight})
    assert "access-control-allow-origin" not in evil.headers
    assert ours.headers["access-control-allow-origin"] == "https://app.example.com"


# ── Authentication ────────────────────────────────────────────────────────────

def test_admin_token_round_trip_and_tamper_detection():
    token = create_access_token({"sub": "admin@example.com"})
    assert verify_token(token)["type"] == "admin"
    assert verify_token(token[:-2] + "xx") is None


def test_customer_token_cannot_access_admin_routes():
    token = create_customer_access_token(str(uuid.uuid4()), "customer@example.com")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("path", [
    "/api/v1/admin/sites",
    "/api/v1/admin/purchase-statistics",
    "/api/v1/subscriptions/admin/statistics",
])
def test_admin_endpoints_require_authentication(path):
    assert path in API_PATHS
    assert client.get(path).status_code in (401, 403)


def test_validation_errors_do_not_echo_request_bodies():
    response = client.post("/api/v1/customer/register", json={"email": "not-an-email", "password": "hunter2-secret"})
    assert response.status_code == 422
    assert "hunter2-secret" not in response.text


def test_login_is_rate_limited():
    codes = [
        client.post("/api/v1/auth/unified-login", data={"username": "a@example.com", "password": "x"},
                    headers={"X-Test": "rate-limit"}).status_code
        for _ in range(11)
    ]
    assert 429 not in codes[:10]
    assert codes[-1] == 429


# ── Webhooks ──────────────────────────────────────────────────────────────────

def test_recurrente_rejects_unsigned_webhooks():
    response = client.post("/api/v1/webhooks/recurrente", content=b'{"event_type": "payment_intent.succeeded"}')
    assert response.status_code == 401


def test_recurrente_signature_verification():
    recurrente = RecurrenteClient()
    body = '{"event_type": "payment_intent.succeeded"}'
    assert recurrente.verify_webhook_signature(body, _svix_headers(body))
    assert not recurrente.verify_webhook_signature(body + " ", _svix_headers(body))
    assert not recurrente.verify_webhook_signature(body, _svix_headers(body, timestamp=int(time.time()) - 3600))
    assert not recurrente.verify_webhook_signature(body, _svix_headers(body, secret=b"wrong" * 5))


def test_recurrente_fails_closed_without_secret():
    recurrente = RecurrenteClient()
    recurrente.webhook_secret = None
    body = "{}"
    assert not recurrente.verify_webhook_signature(body, _svix_headers(body))


def test_labsmobile_callbacks_require_token():
    assert client.get("/api/v1/webhooks/labsmobile/status?subid=1").status_code == 403
    assert client.post("/api/v1/webhooks/labsmobile/reply?token=wrong", json={}).status_code == 403
    assert client.get("/api/v1/webhooks/labsmobile/status?token=test-webhook-token").status_code == 200


def test_telnyx_webhooks_require_valid_signature(monkeypatch):
    assert client.post("/api/v1/webhooks/telnyx/status", json={}).status_code == 403  # no key configured

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setattr(get_settings(), "TELNYX_PUBLIC_KEY", base64.b64encode(public_key).decode())

    body, ts = b'{"data": {}}', str(int(time.time()))
    forged = {"telnyx-timestamp": ts, "telnyx-signature-ed25519": base64.b64encode(b"x" * 64).decode()}
    assert client.post("/api/v1/webhooks/telnyx/status", content=body, headers=forged).status_code == 401

    signed = {
        "telnyx-timestamp": ts,
        "telnyx-signature-ed25519": base64.b64encode(private_key.sign(f"{ts}|".encode() + body)).decode(),
        "content-type": "application/json",
    }
    assert client.post("/api/v1/webhooks/telnyx/status", content=body, headers=signed).status_code not in (401, 403)


# ── Input hardening ───────────────────────────────────────────────────────────

def test_click_tracking_redirects_only_to_own_hosts():
    assert _is_allowed_redirect("https://sites.example.com/joes-plumbing")
    assert not _is_allowed_redirect("https://evil.example/phish")
    assert not _is_allowed_redirect("javascript:alert(1)")


def test_prescreener_blocks_internal_addresses():
    assert URLPrescreener._resolves_to_internal_address("localhost")


def test_site_images_block_path_traversal():
    assert client.get("/%2E%2E/img/hero.jpg").status_code in (400, 404)


def test_domain_provisioning_rejects_shell_metacharacters():
    assert _is_safe_hostname("my-shop.co.uk")
    assert not _is_safe_hostname("x.com; rm -rf /")
    assert not _is_safe_hostname("$(whoami).com")

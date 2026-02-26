"""
LabsMobile SMS Provider.

Implements SMSProvider using the LabsMobile HTTP/POST REST API.
Authentication: Basic Auth (base64-encoded username:token).

API reference: https://www.labsmobile.com/en/sms-api/api-versions/http-rest-post-json

Verified behavior (live curl tests, Feb 2026):
  - Both E.164 (+502...) and plain (502...) phone formats are accepted.
  - Success check: str(response["code"]) == "0"  (balance returns int 0,
    send returns string "0" — normalize both).
  - HTTP 200 on success, HTTP 400 on payload errors, HTTP 401 on auth failure.
  - "subid" is always returned and acts as the message identifier.
  - Cost is not included in the send response (no webhook cost data either).

Author: WebMagic Team
Date: February 2026
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)

LABSMOBILE_SEND_URL = "https://api.labsmobile.com/json/send"
LABSMOBILE_BALANCE_URL = "https://api.labsmobile.com/json/balance"

# Path on our own API that LabsMobile will call for delivery status GET callbacks
WEBHOOK_STATUS_PATH = "/api/v1/webhooks/labsmobile/status"


class LabsMobileSMSProvider:
    """
    LabsMobile SMS provider using Basic HTTP Auth.

    Implements the same interface as TelnyxSMSProvider so SMSSender can
    swap providers without touching any calling code.
    """

    webhook_status_path: str = WEBHOOK_STATUS_PATH

    def __init__(self) -> None:
        settings = get_settings()
        self.username: str = settings.LABSMOBILE_USERNAME or ""
        self.token: str = settings.LABSMOBILE_TOKEN or ""
        self.from_phone: str = settings.LABSMOBILE_PHONE_NUMBER or ""

        if not self.username or not self.token:
            raise ValueError(
                "LabsMobile credentials not configured. "
                "Set LABSMOBILE_USERNAME and LABSMOBILE_TOKEN in .env"
            )

        logger.info("LabsMobile SMS provider initialized")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        status_callback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an SMS via LabsMobile.

        Args:
            to_phone: Recipient phone.  E.164 format accepted (+ prefix is fine).
            body: SMS message text.
            from_phone: Optional sender ID / alphanumeric name (tpoa, max 11 chars).
            status_callback: Optional URL for delivery status GET callbacks (ackurl).

        Returns:
            Normalised dict compatible with the rest of the SMS pipeline:
            {
                "provider":       "labsmobile",
                "message_id":     str,   # LabsMobile subid
                "status":         "queued",
                "to":             str,
                "from":           str,
                "body":           str,
                "segments":       1,     # LabsMobile does not report segments
                "cost":           None,  # LabsMobile does not report cost
                "cost_unit":      "USD",
                "sent_at":        None,
                "error_code":     None,
                "error_message":  None,
            }

        Raises:
            ExternalAPIException: on any API or network error.
        """
        sender = from_phone or self.from_phone or "WebMagic"

        payload: Dict[str, Any] = {
            "message": body,
            "tpoa": sender,
            "recipient": [{"msisdn": to_phone}],
        }

        if status_callback:
            payload["ackurl"] = status_callback

        logger.info("Sending SMS via LabsMobile to %s (%d chars)", to_phone, len(body))

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    LABSMOBILE_SEND_URL,
                    json=payload,
                    auth=(self.username, self.token),
                    headers={"Content-Type": "application/json"},
                )

            data = response.json()
            self._raise_for_error(response.status_code, data, to_phone)

            subid = data.get("subid", "")
            logger.info("LabsMobile SMS accepted: subid=%s to=%s", subid, to_phone)

            return {
                "provider": "labsmobile",
                "message_id": subid,
                "status": "queued",
                "to": to_phone,
                "from": sender,
                "body": body,
                "segments": 1,
                "cost": None,
                "cost_unit": "USD",
                "sent_at": None,
                "error_code": None,
                "error_message": None,
            }

        except httpx.TimeoutException:
            msg = f"LabsMobile API timeout sending to {to_phone}"
            logger.error(msg)
            raise ExternalAPIException(msg)

        except httpx.RequestError as exc:
            msg = f"LabsMobile request error: {exc}"
            logger.error(msg)
            raise ExternalAPIException(msg)

        except ExternalAPIException:
            raise

        except Exception as exc:
            msg = f"LabsMobile unexpected error: {exc}"
            logger.error(msg, exc_info=True)
            raise ExternalAPIException(msg)

    async def get_balance(self) -> float:
        """Return current credit balance (float)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    LABSMOBILE_BALANCE_URL,
                    auth=(self.username, self.token),
                )
            data = response.json()
            if str(data.get("code", "")) != "0":
                raise ExternalAPIException(
                    f"LabsMobile balance error: {data.get('message')}"
                )
            return float(data.get("credits", 0))
        except ExternalAPIException:
            raise
        except Exception as exc:
            raise ExternalAPIException(f"LabsMobile balance check failed: {exc}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_error(
        http_status: int,
        data: Dict[str, Any],
        to_phone: str,
    ) -> None:
        """
        Raise ExternalAPIException when the response signals failure.

        LabsMobile always returns HTTP 200 for success and HTTP 400 for
        payload errors. Auth failures are HTTP 401. We also check the
        JSON "code" field because the API returns code "0" (string) on
        success and a non-zero string on failure — normalise with str().
        """
        if http_status == 401:
            raise ExternalAPIException("LabsMobile authentication failed (check credentials)")

        code = str(data.get("code", ""))
        api_message = data.get("message", "Unknown error")

        if code != "0":
            logger.error(
                "LabsMobile API error code=%s msg=%s to=%s",
                code, api_message, to_phone,
            )
            raise ExternalAPIException(
                f"LabsMobile error {code}: {api_message}"
            )

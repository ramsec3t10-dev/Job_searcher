"""EMBEDHUNT AI — SMS delivery (pluggable; Twilio when configured).

Returns True when a real SMS was handed to a provider. When no provider is
configured (local/dev), returns False and the caller may surface the code
through a dev channel instead.
"""
from __future__ import annotations

import httpx

from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


async def send_sms(phone: str, body: str) -> bool:
    sid, token, sender = (settings.TWILIO_ACCOUNT_SID,
                          settings.TWILIO_AUTH_TOKEN,
                          settings.TWILIO_FROM_NUMBER)
    if not (sid and token and sender):
        logger.info("sms_dev_mode", phone=phone[-4:].rjust(len(phone), "*"))
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, token),
                data={"To": phone, "From": sender, "Body": body},
            )
        ok = r.status_code in (200, 201)
        if not ok:
            logger.warning("sms_send_failed", status=r.status_code)
        return ok
    except httpx.HTTPError as e:
        logger.warning("sms_send_error", error=str(e))
        return False

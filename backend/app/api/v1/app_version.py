"""EMBEDHUNT AI — Mobile app version / in-app update channel.

The Flutter app polls ``GET /api/v1/app/version`` on launch and every 30
minutes. When a newer ``version_code`` is published it prompts the user to
download and install the new APK — no manual uninstall/reinstall.

CI publishes new releases with ``POST /api/v1/app/version/update`` guarded by
the ``X-Update-Secret`` header (``settings.APP_UPDATE_SECRET``).

The active config is persisted to ``settings.MOBILE_VERSION_FILE`` so it
survives across worker processes; if the file is missing the values fall back
to the settings defaults.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/app", tags=["App Update"])

_VERSION_PATH = Path(settings.MOBILE_VERSION_FILE)


class VersionConfig(BaseModel):
    """The version payload served to and published by clients/CI."""

    latest_version: str = Field(..., examples=["1.2.0"])
    version_code: int = Field(..., ge=1, examples=[10200])
    apk_url: str = ""
    mandatory: bool = False
    release_notes: str = ""
    min_supported_version: str = "1.0.0"
    released_at: str = ""


def _defaults() -> VersionConfig:
    return VersionConfig(
        latest_version=settings.MOBILE_LATEST_VERSION,
        version_code=settings.MOBILE_VERSION_CODE,
        apk_url=settings.MOBILE_APK_URL,
        mandatory=False,
        release_notes="",
        min_supported_version=settings.MOBILE_MIN_SUPPORTED_VERSION,
        released_at="",
    )


def _load() -> VersionConfig:
    try:
        if _VERSION_PATH.exists():
            return VersionConfig(**json.loads(_VERSION_PATH.read_text("utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("mobile_version_read_failed", error=str(exc))
    return _defaults()


def _save(config: VersionConfig) -> None:
    try:
        _VERSION_PATH.write_text(config.model_dump_json(indent=2), "utf-8")
    except OSError as exc:
        logger.error("mobile_version_write_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to persist version config")


@router.get("/version", summary="Current published mobile app version")
async def get_version() -> dict:
    """Return the currently published version. Called by every running app."""
    return _load().model_dump()


class PublishVersion(BaseModel):
    latest_version: str
    version_code: int = Field(..., ge=1)
    apk_url: str
    mandatory: bool = False
    release_notes: str = ""
    min_supported_version: str = "1.0.0"


@router.post("/version/update", summary="Publish a new mobile version (CI only)")
async def publish_version(
    payload: PublishVersion,
    x_update_secret: str | None = Header(default=None, alias="X-Update-Secret"),
) -> dict:
    """Publish a new version. Guarded by the ``X-Update-Secret`` header."""
    if not x_update_secret or x_update_secret != settings.APP_UPDATE_SECRET:
        logger.warning("mobile_version_publish_denied")
        raise HTTPException(status_code=403, detail="Invalid update secret")

    config = VersionConfig(
        **payload.model_dump(),
        released_at=datetime.now(timezone.utc).isoformat(),
    )
    _save(config)
    logger.info(
        "mobile_version_published",
        version=config.latest_version,
        code=config.version_code,
    )
    return {"success": True, "data": config.model_dump()}

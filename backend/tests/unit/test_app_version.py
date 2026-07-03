"""Tests for the mobile app-version / in-app update API."""
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.v1.app_version as av
from app.config.settings import settings


@pytest.fixture
def version_file(tmp_path, monkeypatch):
    p = tmp_path / "mobile_version.json"
    monkeypatch.setattr(av, "_VERSION_PATH", p)
    return p


async def _client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_get_version_defaults(version_file):
    async with await _client() as c:
        r = await c.get("/api/v1/app/version")
    assert r.status_code == 200
    d = r.json()
    for key in ("latest_version", "version_code", "apk_url",
                "minimum_version", "force_update", "release_notes"):
        assert key in d
    assert isinstance(d["release_notes"], list)


@pytest.mark.asyncio
async def test_publish_requires_secret(version_file):
    async with await _client() as c:
        r = await c.post("/api/v1/app/version/update", json={
            "latest_version": "1.2.0", "version_code": 10200, "apk_url": "https://x/a.apk",
        })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_publish_wrong_secret(version_file):
    async with await _client() as c:
        r = await c.post("/api/v1/app/version/update",
                         headers={"X-Update-Secret": "nope"},
                         json={"latest_version": "1.2.0", "version_code": 10200,
                               "apk_url": "https://x/a.apk"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_publish_then_get(version_file):
    payload = {
        "latest_version": "1.2.0", "version_code": 10200,
        "apk_url": "https://x/embedhunt-v1.2.0.apk", "minimum_version": "1.1.0",
        "force_update": True, "release_notes": ["Resume upload", "Faster matching"],
    }
    async with await _client() as c:
        pub = await c.post("/api/v1/app/version/update",
                           headers={"X-Update-Secret": settings.APP_UPDATE_SECRET},
                           json=payload)
        assert pub.status_code == 200
        got = (await c.get("/api/v1/app/version")).json()
    assert got["latest_version"] == "1.2.0"
    assert got["version_code"] == 10200
    assert got["force_update"] is True
    assert got["release_notes"] == ["Resume upload", "Faster matching"]
    assert got["released_at"]  # stamped on publish


@pytest.mark.asyncio
async def test_rollback_by_lowering_version_code(version_file):
    async with await _client() as c:
        headers = {"X-Update-Secret": settings.APP_UPDATE_SECRET}
        await c.post("/api/v1/app/version/update", headers=headers,
                     json={"latest_version": "1.2.0", "version_code": 10200, "apk_url": "u"})
        await c.post("/api/v1/app/version/update", headers=headers,
                     json={"latest_version": "1.1.9", "version_code": 10109, "apk_url": "u"})
        got = (await c.get("/api/v1/app/version")).json()
    # rollback: server now advertises the older build; clients on 10200 won't be prompted
    assert got["version_code"] == 10109
    assert got["latest_version"] == "1.1.9"


def test_load_migrates_legacy_fields(version_file):
    version_file.write_text(json.dumps({
        "latest_version": "1.0.5", "version_code": 10005, "apk_url": "u",
        "min_supported_version": "1.0.0", "mandatory": True,
        "release_notes": "Single string note",
    }), "utf-8")
    cfg = av._load()
    assert cfg.minimum_version == "1.0.0"
    assert cfg.force_update is True
    assert cfg.release_notes == ["Single string note"]

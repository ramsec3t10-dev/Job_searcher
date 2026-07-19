"""OTP registration + single-session enforcement tests."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.services.auth_service import AuthService


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


PHONE = "+919876543210"


async def _register(db, phone=PHONE, email="a@b.dev", username="ada_l"):
    svc = AuthService(db)
    otp = await svc.request_otp(phone)
    assert "dev_code" in otp, "dev mode must surface the code"
    return await svc.register(
        email=email, username=username, password="Secure123!",
        first_name="Ada", last_name="Lovelace",
        phone=phone, otp_code=otp["dev_code"],
    )


@pytest.mark.asyncio
async def test_register_requires_phone_and_otp(db):
    svc = AuthService(db)
    with pytest.raises(Exception) as e:
        await svc.register(email="x@y.dev", username="no_phone",
                           password="Secure123!", first_name="A", last_name="B")
    assert "422" in str(getattr(e.value, "status_code", e.value))


@pytest.mark.asyncio
async def test_full_otp_register_flow(db):
    out = await _register(db)
    assert out["user"]["email"] == "a@b.dev"
    assert out["access_token"] and out["refresh_token"]


@pytest.mark.asyncio
async def test_wrong_otp_rejected_and_attempts_limited(db):
    svc = AuthService(db)
    await svc.request_otp(PHONE)
    for _ in range(2):
        with pytest.raises(Exception):
            await svc.register(email="a@b.dev", username="ada_l",
                               password="Secure123!", first_name="A",
                               last_name="B", phone=PHONE, otp_code="000000")


@pytest.mark.asyncio
async def test_phone_number_is_single_use(db):
    await _register(db)
    svc = AuthService(db)
    with pytest.raises(Exception) as e:
        await svc.request_otp(PHONE)
    assert "already registered" in str(e.value.detail)


@pytest.mark.asyncio
async def test_second_login_kills_first_session(db):
    await _register(db)
    svc = AuthService(db)
    first = await svc.login("a@b.dev", "Secure123!")
    second = await svc.login("a@b.dev", "Secure123!")
    # The newest session refreshes fine; the older one is dead.
    ok = await svc.refresh(second["refresh_token"])
    assert ok["access_token"]
    with pytest.raises(Exception) as e:
        await svc.refresh(first["refresh_token"])
    assert "another device" in str(e.value.detail)

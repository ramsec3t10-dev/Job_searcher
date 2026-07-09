"""EMBEDHUNT AI — FastAPI Application"""
import time, uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config.settings import settings
from app.config.logging import setup_logging, get_logger, set_correlation_id
from app.core.lifecycle import lifespan
from app.api.router import api_router
from app.api.v1.ai_features import AIUnavailableError


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME, version=settings.APP_VERSION,
    description="AI-powered career platform for Embedded Software Engineers",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Correlation-ID"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Prometheus metrics at /metrics (request count + latency by route).
from app.config.metrics import setup_metrics
setup_metrics(app)

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(cid)
    start = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Response-Time"] = f"{ms}ms"
    logger.info("http", method=request.method, path=request.url.path, status=response.status_code, ms=ms)
    return response

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    errors = [{"field": ".".join(str(l) for l in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"success": False, "error": "Validation Error", "details": errors})

@app.exception_handler(AIUnavailableError)
async def ai_unavailable_handler(request, exc: AIUnavailableError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.error,
            "message": exc.message,
            "fallback_available": exc.fallback_available,
        },
    )

@app.exception_handler(Exception)
async def generic_handler(request, exc):
    from app.core.exceptions import EmbedHuntException
    if isinstance(exc, EmbedHuntException):
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message})
    logger.error("unhandled", error=str(exc), path=str(request.url))
    msg = str(exc) if not settings.is_production else "Internal server error"
    return JSONResponse(status_code=500, content={"success": False, "error": msg})

@app.get("/health", tags=["System"])
async def health(): return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@app.get("/health/ready", tags=["System"])
async def ready():
    from app.database.dependency import check_db_connection
    ok = await check_db_connection()
    return JSONResponse(status_code=200 if ok else 503, content={"status": "ready" if ok else "not_ready", "db": "ok" if ok else "error"})

@app.get("/", include_in_schema=False)
async def root(): return {"app": settings.APP_NAME, "docs": "/docs", "health": "/health"}

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

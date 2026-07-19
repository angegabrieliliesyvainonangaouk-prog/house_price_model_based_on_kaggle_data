import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import init_db
from cerveau.prediction import ModelLoader
from auth import get_client_ip
from routes import router, _rate_limit_combined, RATE_LIMIT_PER_IP, RATE_LIMIT_WINDOW, APP_NAME, APP_VERSION

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"API: starting {APP_NAME} v{APP_VERSION}")

    try:
        ModelLoader.load()
        logger.info("API: ML models loaded")
    except Exception as e:
        logger.warning(f"API: could not load ML models: {e}")

    try:
        await init_db()
        logger.info("API: database tables ensured")
    except Exception as e:
        logger.warning(f"API: could not create tables: {e}")

    logger.info("API: ready")
    yield
    logger.info("API: shutdown")


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"field": ".".join(str(x) for x in e["loc"] if x != "body"), "message": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ]
        },
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/auth"):
        ip = get_client_ip(request)
        fingerprint = request.headers.get("X-Fingerprint", "")
        if not _rate_limit_combined(ip, fingerprint, RATE_LIMIT_PER_IP, RATE_LIMIT_WINDOW):
            return JSONResponse(status_code=429, content={"error": "Too many requests", "detail": "Limite de taux atteinte.", "retry_after": RATE_LIMIT_WINDOW})
    return await call_next(request)


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/html", StaticFiles(directory=str(FRONTEND_DIR / "html")), name="html")

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=4)

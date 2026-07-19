import os
import sys
import hashlib
import time
import logging
import csv
import io
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response, Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from prediction import (
    predict_normal, predict_csv,
    ModelLoader, FEATURE_NAMES, COLUMNS_GUIDE, COLUMNS_GUIDE_MAP,
    FEATURE_COUNT, ONE_HOT_GROUPS
)

from auth import (
    get_db, hash_password, verify_password, generate_default_password,
    create_access_token, create_refresh_token, decode_token, hash_token,
    set_auth_cookies, clear_auth_cookies, get_client_ip, verify_csrf
)
from email_service import send_welcome_email, send_password_change_confirmation

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "ML Predictor Pro")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
MAX_CSV_ROWS = int(os.getenv("MAX_CSV_ROWS", "1461"))
RATE_LIMIT_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
DAILY_TOKEN_LIMIT = int(os.getenv("DAILY_TOKEN_LIMIT", "20"))
TOKEN_WINDOW = int(os.getenv("TOKEN_WINDOW", "86400"))

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_PRODUCT_ID = os.getenv("PAYPAL_PRODUCT_ID", "")
PAYPAL_PRICE_ID = os.getenv("PAYPAL_PRICE_ID", "")
CLEANING_PRICE = os.getenv("CLEANING_PRICE", "1.00")

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

_rate_store = defaultdict(list)
_token_store = defaultdict(list)
_fingerprint_rate_store = defaultdict(list)

_paypal_token_cache = {"token": "", "expires": 0}
_paypal_orders = set()

_pred_executor = ThreadPoolExecutor(max_workers=4)
_ml_metadata_cache = None


def _rate_limit_combined(ip: str, fingerprint: str, limit: int, window: int) -> bool:
    now = time.time()
    combined_key = f"{ip}:{fingerprint}" if fingerprint else ip
    times = _rate_store[combined_key]
    cutoff = now - window
    while times and times[0] < cutoff:
        times.pop(0)
    if len(times) >= limit:
        return False
    times.append(now)
    return True


def _rate_limit_token(token: str, limit: int, window: int) -> bool:
    now = time.time()
    times = _token_store[token]
    cutoff = now - window
    while times and times[0] < cutoff:
        times.pop(0)
    if len(times) >= limit:
        return False
    times.append(now)
    return True


def _generate_token(ip: str) -> str:
    raw = f"{ip}:{int(time.time() / TOKEN_WINDOW)}:{os.urandom(4).hex()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def _get_metadata():
    global _ml_metadata_cache
    if _ml_metadata_cache:
        return _ml_metadata_cache
    _ml_metadata_cache = {
        "feature_names": FEATURE_NAMES,
        "feature_count": FEATURE_COUNT,
        "one_hot_groups": {k: list(v) for k, v in ONE_HOT_GROUPS.items()},
        "columns_guide": COLUMNS_GUIDE,
        "columns_guide_map": COLUMNS_GUIDE_MAP,
    }
    return _ml_metadata_cache


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[dict]:
    access_token = request.cookies.get("access_token", "")
    if not access_token:
        return None
    payload = decode_token(access_token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    result = await db.execute(text("SELECT id, email, is_active, default_password_used FROM users WHERE id = :uid"), {"uid": user_id})
    row = result.mappings().first()
    if not row or not row["is_active"]:
        return None
    return dict(row)


async def require_auth(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not verify_csrf(request, csrf_header):
        raise HTTPException(status_code=403, detail="Token CSRF invalide")
    return user


TRAIN_COLUMNS = [
    "Id", "MSSubClass", "MSZoning", "LotFrontage", "LotArea", "Street", "Alley",
    "LotShape", "LandContour", "Utilities", "LotConfig", "LandSlope", "Neighborhood",
    "Condition1", "Condition2", "BldgType", "HouseStyle", "OverallQual", "OverallCond",
    "YearBuilt", "YearRemodAdd", "RoofStyle", "RoofMatl", "Exterior1st", "Exterior2nd",
    "MasVnrType", "MasVnrArea", "ExterQual", "ExterCond", "Foundation", "BsmtQual",
    "BsmtCond", "BsmtExposure", "BsmtFinType1", "BsmtFinSF1", "BsmtFinType2",
    "BsmtFinSF2", "BsmtUnfSF", "TotalBsmtSF", "Heating", "HeatingQC", "CentralAir",
    "Electrical", "1stFlrSF", "2ndFlrSF", "LowQualFinSF", "GrLivArea", "BsmtFullBath",
    "BsmtHalfBath", "FullBath", "HalfBath", "BedroomAbvGr", "KitchenAbvGr",
    "KitchenQual", "TotRmsAbvGrd", "Functional", "Fireplaces", "FireplaceQu",
    "GarageType", "GarageYrBlt", "GarageFinish", "GarageCars", "GarageArea",
    "GarageQual", "GarageCond", "PavedDrive", "WoodDeckSF", "OpenPorchSF",
    "EnclosedPorch", "3SsnPorch", "ScreenPorch", "PoolArea", "PoolQC", "Fence",
    "MiscFeature", "MiscVal", "MoSold", "YrSold", "SaleType", "SaleCondition",
]


CREATE_TABLES_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    default_password_used BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    fingerprint_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

CREATE TABLE IF NOT EXISTS login_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email_attempted VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    fingerprint_hash VARCHAR(255),
    success BOOLEAN DEFAULT FALSE,
    failure_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_audit_ip ON login_audit(ip_address);
CREATE INDEX IF NOT EXISTS idx_login_audit_time ON login_audit(created_at);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"API: starting {APP_NAME} v{APP_VERSION}")

    try:
        ModelLoader.load()
        logger.info("API: ML models loaded")
    except Exception as e:
        logger.warning(f"API: could not load ML models: {e}")

    try:
        from auth import async_session
        async with async_session() as session:
            for statement in CREATE_TABLES_SQL.split(";"):
                stmt = statement.strip()
                if stmt:
                    await session.execute(text(stmt))
            await session.commit()
        logger.info("API: database tables ensured")
    except Exception as e:
        logger.warning(f"API: could not create tables: {e}")

    logger.info("API: ready")
    yield
    _pred_executor.shutdown(wait=False)
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


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    html_path = FRONTEND_DIR / "login.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Login page not found</h1>")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    html_path = FRONTEND_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ML Predictor Pro</h1><p>Frontend not found.</p>")


@app.get("/api/v1/me")
async def get_me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifie")
    return {"id": user["id"], "email": user["email"], "must_change_password": user.get("default_password_used", False)}


@app.post("/api/v1/auth/register")
async def auth_register(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="E-mail et mot de passe requis")
    if not email.endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Seules les adresses Gmail sont acceptees")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit faire au moins 8 caracteres")

    existing = await db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
    if existing.mappings().first():
        raise HTTPException(status_code=409, detail="Un compte existe deja avec cet e-mail")

    default_pwd = generate_default_password()
    default_pwd_hash = hash_password(default_pwd)
    user_pwd_hash = hash_password(password)

    await db.execute(
        text("INSERT INTO users (email, password_hash, is_verified, default_password_used) VALUES (:email, :pwd, :verified, :default_used)"),
        {"email": email, "pwd": user_pwd_hash, "verified": False, "default_used": True}
    )
    await db.commit()

    await send_welcome_email(email, default_pwd)

    ip = get_client_ip(request)
    fingerprint = request.headers.get("X-Fingerprint", "unknown")
    await db.execute(
        text("INSERT INTO login_audit (email_attempted, ip_address, fingerprint_hash, success, failure_reason) VALUES (:email, :ip, :fp, :ok, :reason)"),
        {"email": email, "ip": ip, "fp": hash_token(fingerprint), "ok": True, "reason": "registration"}
    )
    await db.commit()

    return {"message": "Compte cree. Un e-mail avec le mot de passe par defaut a ete envoye."}


@app.post("/api/v1/auth/login")
async def auth_login(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password", "")
    fingerprint = request.headers.get("X-Fingerprint", "unknown")
    ip = get_client_ip(request)

    if not email or not password:
        raise HTTPException(status_code=400, detail="E-mail et mot de passe requis")

    result = await db.execute(
        text("SELECT id, password_hash, is_active, default_password_used, login_attempts, locked_until FROM users WHERE email = :email"),
        {"email": email}
    )
    row = result.mappings().first()

    if not row:
        await db.execute(
            text("INSERT INTO login_audit (email_attempted, ip_address, fingerprint_hash, success, failure_reason) VALUES (:email, :ip, :fp, :ok, :reason)"),
            {"email": email, "ip": ip, "fp": hash_token(fingerprint), "ok": False, "reason": "user_not_found"}
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect")

    if row["locked_until"] and row["locked_until"] > datetime.now(timezone.utc):
        raise HTTPException(status_code=423, detail="Compte temporairement bloque. Reessayez plus tard.")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Compte desactive")

    if not verify_password(password, row["password_hash"]):
        new_attempts = (row["login_attempts"] or 0) + 1
        lock_until = None
        if new_attempts >= 5:
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            new_attempts = 0
        await db.execute(
            text("UPDATE users SET login_attempts = :attempts, locked_until = :locked WHERE id = :uid"),
            {"attempts": new_attempts, "locked": lock_until, "uid": row["id"]}
        )
        await db.execute(
            text("INSERT INTO login_audit (user_id, email_attempted, ip_address, fingerprint_hash, success, failure_reason) VALUES (:uid, :email, :ip, :fp, :ok, :reason)"),
            {"uid": row["id"], "email": email, "ip": ip, "fp": hash_token(fingerprint), "ok": False, "reason": "wrong_password"}
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect")

    await db.execute(
        text("UPDATE users SET login_attempts = 0, locked_until = NULL, last_login = NOW() WHERE id = :uid"),
        {"uid": row["id"]}
    )
    await db.execute(
        text("INSERT INTO login_audit (user_id, email_attempted, ip_address, fingerprint_hash, success) VALUES (:uid, :email, :ip, :fp, :ok)"),
        {"uid": row["id"], "email": email, "ip": ip, "fp": hash_token(fingerprint), "ok": True}
    )
    await db.commit()

    access_token = create_access_token(row["id"], email)
    refresh_token = create_refresh_token(row["id"])

    refresh_hash = hash_token(refresh_token)
    await db.execute(
        text("INSERT INTO refresh_tokens (user_id, token_hash, fingerprint_hash, ip_address, user_agent, expires_at) VALUES (:uid, :th, :fp, :ip, :ua, :exp)"),
        {
            "uid": row["id"], "th": refresh_hash, "fp": hash_token(fingerprint),
            "ip": ip, "ua": request.headers.get("User-Agent", ""),
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
    )
    await db.commit()

    set_auth_cookies(response, access_token, refresh_token, secure=COOKIE_SECURE, domain=COOKIE_DOMAIN)

    return {
        "message": "Connexion reussie",
        "must_change_password": bool(row["default_password_used"]),
    }


@app.post("/api/v1/auth/logout")
async def auth_logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token", "")
    if refresh_token:
        rth = hash_token(refresh_token)
        await db.execute(text("UPDATE refresh_tokens SET revoked = true WHERE token_hash = :th"), {"th": rth})
        await db.commit()
    clear_auth_cookies(response, domain=COOKIE_DOMAIN)
    return {"message": "Deconnexion reussie"}


@app.post("/api/v1/auth/refresh")
async def auth_refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token", "")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    rth = hash_token(refresh_token)
    result = await db.execute(
        text("SELECT id, user_id, revoked, expires_at FROM refresh_tokens WHERE token_hash = :th"),
        {"th": rth}
    )
    row = result.mappings().first()
    if not row or row["revoked"] or row["expires_at"] < datetime.now(timezone.utc):
        clear_auth_cookies(response, domain=COOKIE_DOMAIN)
        raise HTTPException(status_code=401, detail="Refresh token expire ou revoque")

    user_result = await db.execute(
        text("SELECT id, email, is_active FROM users WHERE id = :uid"),
        {"uid": row["user_id"]}
    )
    user = user_result.mappings().first()
    if not user or not user["is_active"]:
        clear_auth_cookies(response, domain=COOKIE_DOMAIN)
        raise HTTPException(status_code=401, detail="Compte invalide")

    new_access = create_access_token(user["id"], user["email"])
    new_refresh = create_refresh_token(user["id"])

    await db.execute(text("UPDATE refresh_tokens SET revoked = true WHERE token_hash = :th"), {"th": rth})
    new_rth = hash_token(new_refresh)
    fingerprint = request.headers.get("X-Fingerprint", "unknown")
    ip = get_client_ip(request)
    await db.execute(
        text("INSERT INTO refresh_tokens (user_id, token_hash, fingerprint_hash, ip_address, user_agent, expires_at) VALUES (:uid, :th, :fp, :ip, :ua, :exp)"),
        {
            "uid": user["id"], "th": new_rth, "fp": hash_token(fingerprint),
            "ip": ip, "ua": request.headers.get("User-Agent", ""),
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
    )
    await db.commit()

    set_auth_cookies(response, new_access, new_refresh, secure=COOKIE_SECURE, domain=COOKIE_DOMAIN)
    return {"message": "Token rafraichi"}


@app.post("/api/v1/auth/change-password")
async def auth_change_password(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Ancien et nouveau mot de passe requis")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit faire au moins 8 caracteres")

    access_token = request.cookies.get("access_token", "")
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Non authentifie")

    user_id = payload["sub"]
    result = await db.execute(text("SELECT password_hash FROM users WHERE id = :uid"), {"uid": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")

    if not verify_password(old_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")

    new_hash = hash_password(new_password)
    await db.execute(
        text("UPDATE users SET password_hash = :pwd, default_password_used = false, updated_at = NOW() WHERE id = :uid"),
        {"pwd": new_hash, "uid": user_id}
    )
    await db.commit()

    result = await db.execute(text("SELECT email FROM users WHERE id = :uid"), {"uid": user_id})
    user_email = result.scalar()
    if user_email:
        await send_password_change_confirmation(user_email)

    return {"message": "Mot de passe modifie avec succes"}


@app.post("/api/v1/predict/normal")
async def predict_normal_endpoint(request: Request, user: dict = Depends(require_auth)):
    body = await request.json()
    ip = get_client_ip(request)
    fingerprint = request.headers.get("X-Fingerprint", "")
    token_key = f"user:{user['id']}"
    if not _rate_limit_token(token_key, DAILY_TOKEN_LIMIT, TOKEN_WINDOW):
        raise HTTPException(status_code=429, detail="Limite quotidienne de predictions atteinte.")
    try:
        model_name = body.get("model", "xgboost")
        features = body.get("features", {})
        loop = asyncio.get_event_loop()
        prediction = await loop.run_in_executor(
            _pred_executor, predict_normal, model_name, features
        )
        return {"model": model_name, "prediction": round(prediction, 2), "currency": "USD"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Erreur de prediction")


@app.post("/api/v1/predict/csv")
async def predict_csv_endpoint(request: Request, model: str = "xgboost", file: UploadFile = File(...), user: dict = Depends(require_auth)):
    if model not in ("catboost", "xgboost"):
        raise HTTPException(status_code=400, detail="Model must be 'catboost' or 'xgboost'")
    token_key = f"user:{user['id']}"
    if not _rate_limit_token(token_key, 3, TOKEN_WINDOW):
        raise HTTPException(status_code=429, detail="Limite d'uploads CSV atteinte (3/jour).")
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptes")
    try:
        content = await file.read()
        text_data = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_data))
        records = list(reader)
        if len(records) > MAX_CSV_ROWS:
            raise HTTPException(status_code=400, detail=f"CSV contient {len(records)} lignes, maximum {MAX_CSV_ROWS}")
        if len(records) == 0:
            raise HTTPException(status_code=400, detail="Fichier CSV vide")
        loop = asyncio.get_event_loop()
        predictions = await loop.run_in_executor(
            _pred_executor, predict_csv, model, records
        )
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Id", "SalePrice"])
        for rec, pred in zip(records, predictions):
            row_id = rec.get("Id", rec.get("id", ""))
            writer.writerow([row_id, f"{pred:.2f}"])
        return Response(content=out.getvalue().encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=predictions.csv"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du traitement CSV")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION, "models_loaded": ModelLoader._loaded}


@app.get("/api/v1/models")
async def models():
    meta = await _get_metadata()
    return {
        "models": ["catboost", "xgboost"],
        "feature_count": meta["feature_count"],
        "feature_names": meta["feature_names"],
        "one_hot_groups": meta["one_hot_groups"],
        "feature_groups": [
            {"name_fr": "General", "name_en": "General", "features": ["MSSubClass", "LotFrontage", "LotArea", "LotShape", "LandContour", "Utilities", "LandSlope"]},
            {"name_fr": "Construction", "name_en": "Construction", "features": ["OverallQual", "OverallCond", "YearBuilt", "YearRemodAdd", "MasVnrArea"]},
            {"name_fr": "Exterieur", "name_en": "Exterior", "features": ["ExterQual", "ExterCond", "RoofStyle", "RoofMatl", "MasVnrType", "Foundation", "Exterior"]},
            {"name_fr": "Sous-sol", "name_en": "Basement", "features": ["BsmtQual", "BsmtCond", "BsmtExposure", "BsmtFinType1", "BsmtFinType2", "BsmtUnfSF", "TotalBsmtSF", "BsmtFinSF"]},
            {"name_fr": "Interieur", "name_en": "Interior", "features": ["HeatingQC", "CentralAir", "LowQualFinSF", "GrLivArea", "BedroomAbvGr", "KitchenAbvGr", "KitchenQual", "TotRmsAbvGrd", "Functional"]},
            {"name_fr": "Equipements", "name_en": "Features", "features": ["Fireplaces", "FireplaceQu", "WoodDeckSF", "OpenPorchSF", "EnclosedPorch", "3SsnPorch", "ScreenPorch", "PoolArea", "PoolQC", "Fence"]},
            {"name_fr": "Garage", "name_en": "Garage", "features": ["GarageFinish", "GarageQual", "GarageCond", "GarageType", "GarageArePerCar", "GarageYrBltp"]},
            {"name_fr": "Terrain & Quartier", "name_en": "Lot & Neighborhood", "features": ["LotConfig", "Condition1", "Condition2", "Neighborhood", "Street", "Alley"]},
            {"name_fr": "Urbanisme & Vente", "name_en": "Zoning & Sale", "features": ["MSZoning", "BldgType", "HouseStyle", "Electrical", "Heating", "SaleType", "SaleCondition", "PavedDrive"]},
            {"name_fr": "Divers", "name_en": "Miscellaneous", "features": ["MiscVal", "MiscFeature", "YearRemodAddp", "TotalFlrsf", "Totalbath"]},
        ],
        "normal_fields": [
            {"name":"OverallQual","label_fr":"Qualite generale (1-10)","desc_fr":"Note de 1 a 10 sur la qualite des materiaux et finitions","label_en":"Overall Quality (1-10)","desc_en":"Rating from 1 to 10 on material and finish quality"},
            {"name":"GrLivArea","label_fr":"Surface habitable (pi2)","desc_fr":"Superficie des pieces a vivre hors sous-sol","label_en":"Living Area (sq ft)","desc_en":"Above grade living area square footage"},
            {"name":"YearBuilt","label_fr":"Annee de construction","desc_fr":"Annee de construction originale","label_en":"Year Built","desc_en":"Original construction year"},
            {"name":"TotalBsmtSF","label_fr":"Surface sous-sol (pi2)","desc_fr":"Superficie totale du sous-sol","label_en":"Basement Area (sq ft)","desc_en":"Total basement area in square feet"},
            {"name":"LotArea","label_fr":"Superficie terrain (pi2)","desc_fr":"Surface totale du terrain","label_en":"Lot Area (sq ft)","desc_en":"Total lot area in square feet"},
            {"name":"BedroomAbvGr","label_fr":"Nombre de chambres","desc_fr":"Chambres hors sous-sol","label_en":"Bedrooms","desc_en":"Number of bedrooms above grade"},
            {"name":"Totalbath","label_fr":"Salles de bains","desc_fr":"Total salles de bains (1 = complete, 0.5 = demi)","label_en":"Bathrooms","desc_en":"Total bathrooms (1 = full, 0.5 = half)"},
            {"name":"Fireplaces","label_fr":"Nombre de cheminees","desc_fr":"Nombre de cheminees dans la maison","label_en":"Fireplaces","desc_en":"Number of fireplaces"},
            {"name":"KitchenQual","label_fr":"Qualite cuisine","desc_fr":"Qualite de la cuisine: Ex, Gd, TA, Fa, Po","label_en":"Kitchen Quality","desc_en":"Kitchen quality: Ex, Gd, TA, Fa, Po"},
            {"name":"CentralAir","label_fr":"Climatisation centrale","desc_fr":"Presence de climatisation centrale: Y/N","label_en":"Central AC","desc_en":"Central air conditioning: Y/N"},
        ],
    }


@app.get("/api/v1/column-guide")
async def column_guide():
    meta = await _get_metadata()
    return {"columns": meta["columns_guide"]}


@app.get("/api/v1/column-guide/{name}")
async def column_guide_item(name: str):
    meta = await _get_metadata()
    if name in meta["columns_guide_map"]:
        return meta["columns_guide_map"][name]
    raise HTTPException(status_code=404, detail="Column not found")


@app.get("/api/v1/template")
async def download_template():
    try:
        from prediction import FEATURE_NAMES
        cols = FEATURE_NAMES
    except ImportError:
        cols = TRAIN_COLUMNS
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    row = {c: "" for c in cols}
    row[cols[0]] = "1"
    writer.writerow(row)
    return Response(
        content=out.getvalue().encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template_161_features.csv"}
    )


@app.post("/api/v1/clean")
async def clean_csv_endpoint(request: Request, file: UploadFile = File(...), user: dict = Depends(require_auth)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptes")
    try:
        content = await file.read()
        text_data = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_data))
        raw_rows = list(reader)
        if len(raw_rows) > MAX_CSV_ROWS:
            raise HTTPException(status_code=400, detail=f"CSV contient {len(raw_rows)} lignes, maximum {MAX_CSV_ROWS}")
        if len(raw_rows) == 0:
            raise HTTPException(status_code=400, detail="Fichier CSV vide")
        from prediction_cleaner import clean_csv
        cleaned_records = clean_csv(text_data)
        if not cleaned_records:
            raise HTTPException(status_code=400, detail="Aucune donnee apres nettoyage")
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(cleaned_records[0].keys()))
        writer.writeheader()
        for rec in cleaned_records:
            writer.writerow(rec)
        return Response(
            content=out.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cleaned.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clean error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du nettoyage")


@app.post("/api/v1/download-cleaned")
async def download_cleaned_endpoint(request: Request, file: UploadFile = File(...), paypal_order_id: str = "", user: dict = Depends(require_auth)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptes")
    if not paypal_order_id:
        raise HTTPException(status_code=400, detail="PayPal order ID requis pour le telechargement")
    try:
        verified = await _verify_paypal_capture(paypal_order_id)
        if not verified:
            raise HTTPException(status_code=402, detail="Paiement PayPal non verifie ou echoue")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PayPal verification error: {e}")
        raise HTTPException(status_code=502, detail="Erreur de verification PayPal")
    try:
        content = await file.read()
        text_data = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_data))
        raw_rows = list(reader)
        if len(raw_rows) > MAX_CSV_ROWS:
            raise HTTPException(status_code=400, detail=f"CSV contient {len(raw_rows)} lignes, maximum {MAX_CSV_ROWS}")
        if len(raw_rows) == 0:
            raise HTTPException(status_code=400, detail="Fichier CSV vide")
        from prediction_cleaner import clean_csv
        cleaned_records = clean_csv(text_data)
        if not cleaned_records:
            raise HTTPException(status_code=400, detail="Aucune donnee apres nettoyage")
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(cleaned_records[0].keys()))
        writer.writeheader()
        for rec in cleaned_records:
            writer.writerow(rec)
        return Response(
            content=out.getvalue().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cleaned.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download cleaned error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du telechargement")


@app.get("/api/v1/raw-columns-guide")
async def raw_columns_guide():
    from prediction_cleaner import TRAIN_COLUMNS as RAW_COLS
    from prediction import COLUMNS_GUIDE_MAP
    columns = []
    for col_name in RAW_COLS:
        guide = COLUMNS_GUIDE_MAP.get(col_name, {})
        columns.append({
            "name": col_name,
            "label_fr": guide.get("label_fr", col_name),
            "label_en": guide.get("label_en", col_name),
            "desc_fr": guide.get("desc_fr", ""),
            "desc_en": guide.get("desc_en", ""),
            "type": guide.get("type", "text"),
            "options": guide.get("options", []),
            "unit": guide.get("unit", ""),
            "min": guide.get("min"),
            "max": guide.get("max"),
        })
    return {"columns": columns, "total": len(columns)}


# --- PayPal ---

async def _get_paypal_access_token() -> str:
    now = time.time()
    if _paypal_token_cache["token"] and _paypal_token_cache["expires"] > now:
        return _paypal_token_cache["token"]
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal non configure (manque CLIENT_ID/SECRET)")
    credentials = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE_URL}/v1/oauth2/token",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            data="grant_type=client_credentials",
            timeout=15.0,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Echec d'authentification PayPal")
        token_data = resp.json()
    _paypal_token_cache["token"] = token_data["access_token"]
    _paypal_token_cache["expires"] = now + token_data.get("expires_in", 3600) - 60
    return _paypal_token_cache["token"]


@app.post("/api/v1/paypal/create")
async def paypal_create_order(request: Request):
    body = await request.json()
    amount = body.get("amount", CLEANING_PRICE)
    currency = body.get("currency_code", "EUR")
    try:
        base_url = str(request.base_url).rstrip("/")
        return_url = f"{base_url}/paypal/return"
        cancel_url = f"{base_url}/static/cleaning.html"
        access_token = await _get_paypal_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Prefer": "return=representation"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "amount": {"currency_code": currency, "value": str(amount)},
                        "description": "Nettoyage de fichier CSV - ML Predictor Pro",
                    }],
                    "application_context": {
                        "brand_name": "ML Predictor Pro",
                        "landing_page": "BILLING",
                        "user_action": "PAY_NOW",
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    },
                },
                timeout=15.0,
            )
            data = resp.json()
            if resp.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail=data.get("message", "Echec de creation de la commande PayPal"))
        order_id = data.get("id", "")
        if not order_id:
            raise HTTPException(status_code=502, detail="PayPal n'a pas renvoye d'order_id")
        _paypal_orders.add(order_id)
        approval_url = ""
        for link in data.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link.get("href", "")
                break
        return {"order_id": order_id, "approval_url": approval_url, "status": data.get("status", "")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PayPal create error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la creation de la commande PayPal")


@app.post("/api/v1/paypal/capture")
async def paypal_capture_order(request: Request):
    body = await request.json()
    order_id = body.get("order_id", "")
    if not order_id:
        raise HTTPException(status_code=400, detail="order_id requis")
    if order_id not in _paypal_orders:
        logger.warning(f"PayPal capture: order_id {order_id} non reconnu")
        raise HTTPException(status_code=403, detail="Commande non reconnue")
    try:
        access_token = await _get_paypal_access_token()
        async with httpx.AsyncClient() as client:
            get_resp = await client.get(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                timeout=15.0,
            )
            if get_resp.status_code != 200:
                _paypal_orders.discard(order_id)
                raise HTTPException(status_code=502, detail="Impossible de recuperer les details de la commande")
            order_data = get_resp.json()
        create_time_str = order_data.get("create_time", "")
        if create_time_str:
            create_time = datetime.fromisoformat(create_time_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_seconds = (now - create_time).total_seconds()
            if age_seconds > 600:
                _paypal_orders.discard(order_id)
                logger.warning(f"PayPal capture: order_id {order_id} expire (age: {age_seconds:.0f}s)")
                raise HTTPException(status_code=403, detail="Commande expiree (plus de 10 minutes)")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Prefer": "return=representation"},
                timeout=15.0,
            )
            data = resp.json()
            if resp.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail=data.get("message", "Echec de capture PayPal"))
        status = data.get("status", "")
        if status != "COMPLETED":
            raise HTTPException(status_code=402, detail=f"Paiement non termine (statut: {status})")
        _paypal_orders.discard(order_id)
        return {"status": "COMPLETED", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PayPal capture error: {e}")
        _paypal_orders.discard(order_id)
        raise HTTPException(status_code=500, detail="Erreur lors de la capture PayPal")


@app.get("/paypal/return")
async def paypal_return(token: str = ""):
    if not token:
        return HTMLResponse(content="""<!DOCTYPE html><html><head><meta charset="utf-8"><title>PayPal</title></head>
<body style="font-family:sans-serif;text-align:center;padding:60px">
<h2>Parametre manquant</h2><p>Aucun token recu de PayPal.</p>
<script>window.close();</script></body></html>""")
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Paiement PayPal - Verification</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 60px 20px; background: #f4f5f7; }}
        .card {{ background: white; border-radius: 12px; padding: 40px; max-width: 400px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .spinner {{ width: 40px; height: 40px; border: 3px solid #e2e5ea; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .success {{ color: #059669; font-weight: 600; }}
        .error {{ color: #dc2626; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="spinner" id="spinner"></div>
        <p id="status">Verification du paiement...</p>
    </div>
    <script>
        (async function() {{
            const token = "{token}";
            const statusEl = document.getElementById("status");
            try {{
                const res = await fetch("/api/v1/paypal/capture", {{
                    method: "POST",
                    headers: {{"Content-Type": "application/json"}},
                    body: JSON.stringify({{order_id: token}})
                }});
                const data = await res.json();
                if (res.ok && data.status === "COMPLETED") {{
                    document.getElementById("spinner").style.display = "none";
                    statusEl.className = "success";
                    statusEl.textContent = "Paiement confirme !";
                    if (window.opener) {{
                        window.opener.postMessage({{type: "paypal-success", order_id: token}}, "*");
                    }}
                    setTimeout(function() {{ window.close(); }}, 2000);
                }} else {{
                    document.getElementById("spinner").style.display = "none";
                    statusEl.className = "error";
                    statusEl.textContent = data.detail || "Erreur de verification";
                    setTimeout(function() {{ window.close(); }}, 3000);
                }}
            }} catch(e) {{
                document.getElementById("spinner").style.display = "none";
                statusEl.className = "error";
                statusEl.textContent = "Erreur de connexion";
                setTimeout(function() {{ window.close(); }}, 3000);
            }}
        }})();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


async def _verify_paypal_capture(order_id: str) -> bool:
    try:
        access_token = await _get_paypal_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
        return data.get("status") == "COMPLETED"
    except Exception as e:
        logger.error(f"PayPal verify error: {e}")
        return False


@app.post("/api/v1/paypal/setup")
async def paypal_setup(request: Request):
    body = await request.json()
    client_id = body.get("client_id", "")
    client_secret = body.get("client_secret", "")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="client_id et client_secret requis")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE_URL}/v1/oauth2/token",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            data="grant_type=client_credentials",
            timeout=15.0,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": "Identifiants PayPal invalides"}
        token_data = resp.json()
    access_token = token_data["access_token"]
    async with httpx.AsyncClient() as client:
        prod_resp = await client.post(
            f"{PAYPAL_BASE_URL}/v1/catalogs/products",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"name": "ML Predictor Pro - Nettoyage CSV", "description": "Service de nettoyage et prediction de fichier CSV immobilier", "type": "SERVICE"},
            timeout=15.0,
        )
        if prod_resp.status_code not in (200, 201):
            return {"ok": False, "error": "Echec de creation du produit PayPal"}
        product = prod_resp.json()
        product_id = product.get("id", "")
    async with httpx.AsyncClient() as client:
        price_resp = await client.post(
            f"{PAYPAL_BASE_URL}/v1/pricing/PLANS",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"product_id": product_id, "name": "Nettoyage CSV unique", "billing_cycle": {"tenure_type": "REGULAR", "pricing_scheme": {"fixed_price": {"currency_code": "EUR", "value": CLEANING_PRICE}}, "frequency": {"interval_unit": "MONTH", "interval_count": 1}}, "payment_preferences": {"auto_bill_outstanding": True}},
            timeout=15.0,
        )
        if price_resp.status_code not in (200, 201):
            return {"ok": False, "error": "Echec de creation du prix PayPal", "product_id": product_id}
        price_data = price_resp.json()
    return {
        "ok": True,
        "client_id": client_id,
        "product_id": product_id,
        "plan_id": price_data.get("id", ""),
        "price": CLEANING_PRICE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=4)

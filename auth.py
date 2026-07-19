import os
import secrets
import hashlib
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Define it in Render Dashboard > Environment.")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "CHANGE_ME")
JWT_ALG = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_EXPIRE = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def generate_default_password() -> str:
    return _secrets.token_urlsafe(12)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None


def set_auth_cookies(response, access_token: str, refresh_token: str, secure: bool = False, domain: str = ""):
    kwargs = {
        "httponly": True,
        "secure": secure,
        "samesite": "strict",
        "path": "/",
    }
    if domain:
        kwargs["domain"] = domain
    response.set_cookie("access_token", access_token, max_age=ACCESS_EXPIRE * 60, **kwargs)
    response.set_cookie("refresh_token", refresh_token, max_age=REFRESH_EXPIRE_DAYS * 86400, **kwargs)
    csrf_token = secrets.token_hex(32)
    response.set_cookie("csrf_token", csrf_token, max_age=ACCESS_EXPIRE * 60, httponly=False, secure=secure, samesite="strict", path="/", domain=domain if domain else None)


def clear_auth_cookies(response, domain: str = ""):
    kwargs = {"path": "/", "domain": domain if domain else None}
    response.delete_cookie("access_token", **kwargs)
    response.delete_cookie("refresh_token", **kwargs)
    response.delete_cookie("csrf_token", **kwargs)


def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


def verify_csrf(request, csrf_header: str = None) -> bool:
    cookie_csrf = request.cookies.get("csrf_token", "")
    header_csrf = csrf_header or request.headers.get("X-CSRF-Token", "")
    if not cookie_csrf or not header_csrf:
        return False
    return secrets.compare_digest(cookie_csrf, header_csrf)

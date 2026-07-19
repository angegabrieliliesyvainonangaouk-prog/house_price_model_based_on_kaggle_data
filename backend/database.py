import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL= DATABASE_URL.replace("postgresql://","postgresql+asyncpg://",1)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20) if DATABASE_URL else None
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) if engine else None


async def get_db():
    if not async_session:
        raise RuntimeError("DATABASE_URL is not set. Configure it in Render Dashboard > Environment.")
    async with async_session() as session:
        yield session


CREATE_TABLES_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    default_password_used BOOLEAN DEFAULT TRUE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMPTZ,
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


async def init_db():
    if not async_session:
        return
    async with async_session() as session:
        for statement in CREATE_TABLES_SQL.split(";"):
            stmt = statement.strip()
            if stmt:
                await session.execute(text(stmt))
        await session.commit()

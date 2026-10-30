from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Settings(BaseSettings):
    database_url: str = "sqlite:///./hruta_onecrm.db"
    secret_key: str = "CHANGE_ME_BEFORE_DEPLOYMENT"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    cors_origin_regex: str = r"^https://.*\.vercel\.app$"
    upload_dir: str = "private_uploads"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

import logging
logger = logging.getLogger("uvicorn.error")

def get_normalized_database_url(url: str) -> str:
    """Normalize postgres URLs to use postgresql+psycopg driver required by psycopg 3."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    if "supabase.co" in url and "pooler" not in url:
        logger.warning(
            "====================================================================\n"
            "[WARNING] You are using Supabase Direct Connection (db.*.supabase.co).\n"
            "Render does not support IPv6 and will fail with 'Network is unreachable'.\n"
            "In Supabase Dashboard -> Database -> Connection string, switch from\n"
            "'Direct' to 'Connection Pooler' (Session mode: port 5432 or 6543).\n"
            "===================================================================="
        )
    return url

db_url = get_normalized_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

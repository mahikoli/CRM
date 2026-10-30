from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, settings, SessionLocal
from .models import Role
from .routers import auth, crm, finance, expanded, documents

DEFAULT_ROLES = [
    "Super Admin", "Management", "Sales / Business Development",
    "Internship Coordinator", "Training Coordinator", "Finance / Accounts",
    "Marketing Executive", "Project / Team Manager", "Employee / Intern"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for local development. For production, use Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for name in DEFAULT_ROLES:
            if not db.query(Role).filter(Role.name == name).first(): db.add(Role(name=name))
        db.commit()
    yield

app = FastAPI(title="HRUTA OneCRM API", version="1.0.0", description="Role-based sales, internship, training, partnership, finance, and project CRM API", lifespan=lifespan)
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth.router, prefix="/api/v1")
app.include_router(crm.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")
app.include_router(expanded.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "HRUTA OneCRM API"}

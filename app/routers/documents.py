import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..models import (
    Activity, AuditLog, Contact, Course, DocumentReference, Enrollment, InternshipApplication,
    InternshipCertificate, Invoice, Lead, Opportunity, Partner, PartnershipActivity,
    PartnershipAgreement, PaymentTransaction, Project, ProjectMilestone, ProjectTask,
    ProjectUpdate, Refund, SalesProposal, TrainingBatch, TrainingSession, User, Organization,
)
from ..security import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}
MAGIC_PREFIXES = {
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}

ENTITY_RULES = {
    "lead": (Lead, {"Super Admin", "Management", "Sales / Business Development"}),
    "opportunity": (Opportunity, {"Super Admin", "Management", "Sales / Business Development"}),
    "organization": (Organization, {"Super Admin", "Management", "Sales / Business Development"}),
    "contact": (Contact, {"Super Admin", "Management", "Sales / Business Development"}),
    "activity": (Activity, {"Super Admin", "Management", "Sales / Business Development"}),
    "proposal": (SalesProposal, {"Super Admin", "Management", "Sales / Business Development"}),
    "application": (InternshipApplication, {"Super Admin", "Management", "Internship Coordinator"}),
    "certificate": (InternshipCertificate, {"Super Admin", "Management", "Internship Coordinator"}),
    "course": (Course, {"Super Admin", "Management", "Training Coordinator"}),
    "batch": (TrainingBatch, {"Super Admin", "Management", "Training Coordinator"}),
    "enrollment": (Enrollment, {"Super Admin", "Management", "Training Coordinator"}),
    "session": (TrainingSession, {"Super Admin", "Management", "Training Coordinator"}),
    "partner": (Partner, {"Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"}),
    "partnership_activity": (PartnershipActivity, {"Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"}),
    "agreement": (PartnershipAgreement, {"Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"}),
    "project": (Project, {"Super Admin", "Management", "Project / Team Manager"}),
    "milestone": (ProjectMilestone, {"Super Admin", "Management", "Project / Team Manager"}),
    "project_update": (ProjectUpdate, {"Super Admin", "Management", "Project / Team Manager"}),
    "project_task": (ProjectTask, {"Super Admin", "Management", "Project / Team Manager", "Employee / Intern"}),
    "invoice": (Invoice, {"Super Admin", "Management", "Finance / Accounts"}),
    "payment": (PaymentTransaction, {"Super Admin", "Management", "Finance / Accounts"}),
    "refund": (Refund, {"Super Admin", "Management", "Finance / Accounts"}),
}


def authorize_entity(db: Session, entity_type: str, entity_id: int, user: User):
    config = ENTITY_RULES.get(entity_type)
    if not config:
        raise HTTPException(422, "Unsupported document record type")
    model, allowed_roles = config
    roles = {role.name for role in user.roles}
    if not roles.intersection(allowed_roles):
        raise HTTPException(403, "Your role cannot access documents for this record type")
    record = db.get(model, entity_id)
    if not record:
        raise HTTPException(404, "Linked record not found")

    managers = {"Super Admin", "Management"}
    if entity_type == "lead" and record.owner_id != user.id and not roles.intersection(managers):
        raise HTTPException(403, "Not permitted to access this lead's documents")
    if entity_type == "opportunity" and record.owner_id != user.id and not roles.intersection(managers):
        raise HTTPException(403, "Not permitted to access this opportunity's documents")
    if entity_type == "proposal":
        opportunity = db.get(Opportunity, record.opportunity_id)
        if opportunity.owner_id != user.id and not roles.intersection(managers):
            raise HTTPException(403, "Not permitted to access this proposal's documents")
    if entity_type == "application" and record.coordinator_id != user.id and "Internship Coordinator" in roles and not roles.intersection(managers):
        raise HTTPException(403, "Not permitted to access this application")
    if entity_type == "project_task":
        project = db.get(Project, record.project_id)
        if project.project_manager_id != user.id and not roles.intersection(managers) and record.assignee_id != user.id:
            raise HTTPException(403, "Not permitted to access this project task")
    if entity_type in {"project", "milestone", "project_update"}:
        project_id = record.id if entity_type == "project" else record.project_id
        project = db.get(Project, project_id)
        if project.project_manager_id != user.id and not roles.intersection(managers):
            raise HTTPException(403, "Not permitted to access this project")
    return record


@router.get("")
def list_documents(entity_type: str, entity_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    authorize_entity(db, entity_type, entity_id, user)
    return db.query(DocumentReference).filter_by(entity_type=entity_type, entity_id=entity_id).order_by(DocumentReference.created_at.desc()).all()


@router.post("", status_code=201)
async def upload_document(entity_type: str = Form(...), entity_id: int = Form(...), file: UploadFile = File(...),
                          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    authorize_entity(db, entity_type, entity_id, user)
    original_name = Path(file.filename or "document").name[:255]
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Allowed file types: PDF, DOCX, XLSX, PNG and JPG")
    prefix = MAGIC_PREFIXES[suffix]
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid.uuid4().hex}{suffix}"
    file_path = upload_dir / storage_key
    size = 0
    header = b""
    try:
        with file_path.open("wb") as destination:
            while chunk := await file.read(64 * 1024):
                if not header: header = chunk[:16]
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, "Documents must be 10 MB or smaller")
                destination.write(chunk)
        if not any(header.startswith(magic) for magic in prefix):
            raise HTTPException(415, "The file content does not match its extension")
        content_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        record = DocumentReference(entity_type=entity_type, entity_id=entity_id, file_name=original_name,
                                   storage_key=storage_key, content_type=content_type, size_bytes=size,
                                   uploaded_by_id=user.id)
        db.add(record); db.flush()
        db.add(AuditLog(user_id=user.id, action="document.uploaded", entity_type=entity_type, entity_id=str(entity_id), details=f"document_id={record.id}; file_name={original_name}"))
        db.commit(); db.refresh(record)
        return record
    except Exception:
        if file_path.exists(): file_path.unlink()
        raise
    finally:
        await file.close()


@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(DocumentReference, document_id)
    if not record: raise HTTPException(404, "Document not found")
    authorize_entity(db, record.entity_type, record.entity_id, user)
    base = Path(settings.upload_dir).resolve()
    path = (base / record.storage_key).resolve()
    if path.parent != base or not path.is_file(): raise HTTPException(404, "Document file not found")
    return FileResponse(path, media_type=record.content_type, filename=record.file_name)

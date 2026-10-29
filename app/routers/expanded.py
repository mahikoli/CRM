import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..extended_schemas import (
    AssessmentCreate, AssessmentResultCreate, CertificateCreate, CertificateUpdate,
    ConfigurationUpdate, EnrollmentCreate, EnrollmentUpdate, InternshipApplicationCreate,
    InternshipApplicationUpdate, InternshipAttendanceCreate, InternshipProgramCreate,
    InternshipProgramUpdate, InternshipTaskCreate, InternshipTaskUpdate, InterviewCreate,
    InterviewUpdate, InternAllocationCreate, LearnerFeedbackCreate, MilestoneCreate,
    MilestoneUpdate, NotificationCreate, NotificationRead, PartnerCreate, PartnerUpdate,
    PartnershipActivityCreate, PartnershipAgreementCreate, PartnershipAgreementUpdate,
    ProjectCreate, ProjectTaskCreate, ProjectTaskUpdate, ProjectUpdateCreate,
    ProjectUpdate as ProjectPatch, RefundCreate, RefundDecision, RoleAssignment,
    SalesProposalCreate, SalesProposalUpdate, TrainerCreate, TrainingAttendanceCreate,
    TrainingBatchCreate, TrainingBatchUpdate, TrainingSessionCreate, CourseCreate,
    CourseUpdate,
)
from ..models import (
    AppConfiguration, Assessment, AssessmentResult, AuditLog, Course, Enrollment,
    InternshipApplication, InternshipAttendance, InternshipCertificate, InternshipInterview,
    InternshipProgram, InternshipTask, InternAllocation, LearnerFeedback, Notification,
    Partner, PartnershipActivity, PartnershipAgreement, PipelineHistory, Project,
    ProjectMilestone, ProjectTask, ProjectUpdate, Refund, Role, SalesProposal, Trainer,
    TrainingAttendance, TrainingBatch, TrainingSession, User, Lead, Opportunity, Invoice,
    PaymentTransaction,
)
from ..security import get_current_user, require_roles

router = APIRouter(tags=["Business modules"])

SUPER_ADMIN = ("Super Admin",)
MANAGEMENT = ("Super Admin", "Management")
SALES = ("Super Admin", "Management", "Sales / Business Development")
INTERNSHIP = ("Super Admin", "Management", "Internship Coordinator")
TRAINING = ("Super Admin", "Management", "Training Coordinator")
PARTNERSHIPS = ("Super Admin", "Management", "Sales / Business Development", "Internship Coordinator")
PROJECTS = ("Super Admin", "Management", "Project / Team Manager")
FINANCE = ("Super Admin", "Management", "Finance / Accounts")


def audit(db: Session, user: User, action: str, entity: str, entity_id: int | str, details: str | None = None):
    db.add(AuditLog(user_id=user.id, action=action, entity_type=entity, entity_id=str(entity_id), details=details))


def require_record(db: Session, model, record_id: int | None, label: str):
    if record_id is None:
        return None
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, f"{label} not found")
    return record


def require_project(db: Session, project_id: int, user: User):
    project = require_record(db, Project, project_id, "Project")
    roles = {role.name for role in user.roles}
    if project.project_manager_id != user.id and not roles.intersection(MANAGEMENT):
        raise HTTPException(403, "This project is assigned to another project manager")
    return project


def set_fields(record, values: dict):
    for key, value in values.items():
        setattr(record, key, value)


def as_dict(record, fields: tuple[str, ...]):
    return {field: getattr(record, field) for field in fields}


@router.get("/directory/users")
def user_directory(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return active team identities for assignment dropdowns, without admin-only account controls."""
    return [
        {"id": person.id, "full_name": person.full_name, "roles": [role.name for role in person.roles]}
        for person in db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).limit(500).all()
    ]


# Internship and student lifecycle
@router.get("/internships/programs")
def list_internship_programs(db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    return db.query(InternshipProgram).order_by(InternshipProgram.name).all()


@router.post("/internships/programs", status_code=201)
def create_internship_program(data: InternshipProgramCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = InternshipProgram(**data.model_dump())
    db.add(record); db.flush(); audit(db, user, "internship_program.created", "internship_program", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/internships/programs/{program_id}")
def update_internship_program(program_id: int, data: InternshipProgramUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = require_record(db, InternshipProgram, program_id, "Internship program")
    changes = data.model_dump(exclude_unset=True); set_fields(record, changes)
    audit(db, user, "internship_program.updated", "internship_program", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/applications")
def list_internship_applications(status: str | None = None, program_id: int | None = None, search: str | None = None,
                                 db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternshipApplication)
    if status: query = query.filter(InternshipApplication.status == status)
    if program_id: query = query.filter(InternshipApplication.program_id == program_id)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(InternshipApplication.full_name.ilike(like), InternshipApplication.email.ilike(like), InternshipApplication.college_name.ilike(like)))
    return query.order_by(InternshipApplication.applied_at.desc()).limit(500).all()


@router.post("/internships/applications", status_code=201)
def create_internship_application(data: InternshipApplicationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    require_record(db, InternshipProgram, data.program_id, "Internship program")
    require_record(db, Lead, data.lead_id, "Lead")
    require_record(db, User, data.coordinator_id, "Coordinator")
    email = str(data.email).lower()
    duplicate = db.query(InternshipApplication).filter(InternshipApplication.email == email, InternshipApplication.status.notin_(["rejected", "withdrawn"])).first()
    if duplicate:
        raise HTTPException(409, f"An active application for this email already exists (application #{duplicate.id})")
    values = data.model_dump(); values["email"] = email
    if values.get("coordinator_id") is None: values["coordinator_id"] = user.id
    record = InternshipApplication(**values)
    db.add(record); db.flush(); audit(db, user, "internship_application.created", "internship_application", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/internships/applications/{application_id}")
def update_internship_application(application_id: int, data: InternshipApplicationUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = require_record(db, InternshipApplication, application_id, "Application")
    changes = data.model_dump(exclude_unset=True)
    require_record(db, InternshipProgram, changes.get("program_id"), "Internship program")
    require_record(db, User, changes.get("coordinator_id"), "Coordinator")
    old_status = record.status
    set_fields(record, changes)
    audit(db, user, "internship_application.updated", "internship_application", record.id, f"{old_status}->{record.status}; {','.join(changes)}")
    if record.status == "selected" and not db.query(InternAllocation).filter(InternAllocation.application_id == record.id).first():
        db.add(InternAllocation(application_id=record.id, team_name=record.team_name or "Unassigned", coordinator_id=record.coordinator_id, notes="Initial selection allocation"))
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/interviews")
def list_interviews(application_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternshipInterview)
    if application_id: query = query.filter(InternshipInterview.application_id == application_id)
    return query.order_by(InternshipInterview.scheduled_at.desc()).limit(500).all()


@router.post("/internships/interviews", status_code=201)
def create_interview(data: InterviewCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    application = require_record(db, InternshipApplication, data.application_id, "Application")
    require_record(db, User, data.interviewer_id, "Interviewer")
    record = InternshipInterview(**data.model_dump())
    db.add(record); db.flush()
    if application.coordinator_id and application.coordinator_id != user.id:
        db.add(Notification(user_id=application.coordinator_id, title="Interview scheduled", message=f"An interview was scheduled for {application.full_name}.", related_type="internship_application", related_id=application.id))
    audit(db, user, "internship_interview.created", "internship_interview", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/internships/interviews/{interview_id}")
def update_interview(interview_id: int, data: InterviewUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = require_record(db, InternshipInterview, interview_id, "Interview")
    changes = data.model_dump(exclude_unset=True); require_record(db, User, changes.get("interviewer_id"), "Interviewer")
    set_fields(record, changes); audit(db, user, "internship_interview.updated", "internship_interview", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/allocations")
def list_intern_allocations(application_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternAllocation)
    if application_id: query = query.filter(InternAllocation.application_id == application_id)
    return query.order_by(InternAllocation.assigned_at.desc()).limit(500).all()


@router.post("/internships/allocations", status_code=201)
def create_intern_allocation(data: InternAllocationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    application = require_record(db, InternshipApplication, data.application_id, "Application")
    coordinator = require_record(db, User, data.coordinator_id, "Coordinator")
    record = InternAllocation(**data.model_dump())
    db.add(record); application.team_name = data.team_name
    if coordinator: application.coordinator_id = coordinator.id
    audit(db, user, "intern_allocation.created", "intern_allocation", data.application_id, data.team_name)
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/attendance")
def list_internship_attendance(application_id: int | None = None, start_date: date | None = None, end_date: date | None = None,
                               db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternshipAttendance)
    if application_id: query = query.filter(InternshipAttendance.application_id == application_id)
    if start_date: query = query.filter(InternshipAttendance.attendance_date >= start_date)
    if end_date: query = query.filter(InternshipAttendance.attendance_date <= end_date)
    return query.order_by(InternshipAttendance.attendance_date.desc()).limit(1000).all()


@router.post("/internships/attendance", status_code=201)
def record_internship_attendance(data: InternshipAttendanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    require_record(db, InternshipApplication, data.application_id, "Application")
    exists = db.query(InternshipAttendance).filter_by(application_id=data.application_id, attendance_date=data.attendance_date).first()
    if exists: raise HTTPException(409, "Attendance is already recorded for this intern and date")
    record = InternshipAttendance(**data.model_dump(), recorded_by_id=user.id)
    db.add(record); db.flush(); audit(db, user, "internship_attendance.recorded", "internship_attendance", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/tasks")
def list_internship_tasks(application_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternshipTask)
    if application_id: query = query.filter(InternshipTask.application_id == application_id)
    return query.order_by(InternshipTask.due_date.asc().nullslast()).limit(500).all()


@router.post("/internships/tasks", status_code=201)
def create_internship_task(data: InternshipTaskCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    application = require_record(db, InternshipApplication, data.application_id, "Application")
    record = InternshipTask(**data.model_dump(), assigned_by_id=user.id)
    db.add(record); db.flush()
    if application.coordinator_id and application.coordinator_id != user.id:
        db.add(Notification(user_id=application.coordinator_id, title="Intern task assigned", message=f"A task was added for {application.full_name}.", related_type="internship_application", related_id=application.id))
    audit(db, user, "internship_task.created", "internship_task", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/internships/tasks/{task_id}")
def update_internship_task(task_id: int, data: InternshipTaskUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = require_record(db, InternshipTask, task_id, "Internship task")
    changes = data.model_dump(exclude_unset=True); set_fields(record, changes)
    audit(db, user, "internship_task.updated", "internship_task", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/internships/certificates")
def list_certificates(application_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    query = db.query(InternshipCertificate)
    if application_id: query = query.filter(InternshipCertificate.application_id == application_id)
    return query.order_by(InternshipCertificate.created_at.desc()).limit(500).all()


@router.post("/internships/certificates", status_code=201)
def create_certificate(data: CertificateCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    require_record(db, InternshipApplication, data.application_id, "Application")
    record = InternshipCertificate(**data.model_dump())
    db.add(record); db.flush(); audit(db, user, "internship_certificate.created", "internship_certificate", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/internships/certificates/{certificate_id}")
def update_certificate(certificate_id: int, data: CertificateUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INTERNSHIP))):
    record = require_record(db, InternshipCertificate, certificate_id, "Certificate")
    changes = data.model_dump(exclude_unset=True); set_fields(record, changes)
    if record.status == "issued" and not record.issued_at: record.issued_at = datetime.utcnow()
    audit(db, user, "internship_certificate.updated", "internship_certificate", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


# Training, course, batch and learner progress
@router.get("/training/courses")
def list_courses(db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    return db.query(Course).order_by(Course.name).all()


@router.post("/training/courses", status_code=201)
def create_course(data: CourseCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    record = Course(**data.model_dump()); db.add(record); db.flush()
    audit(db, user, "course.created", "course", record.id); db.commit(); db.refresh(record)
    return record


@router.patch("/training/courses/{course_id}")
def update_course(course_id: int, data: CourseUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    record = require_record(db, Course, course_id, "Course"); changes = data.model_dump(exclude_unset=True)
    set_fields(record, changes); audit(db, user, "course.updated", "course", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/training/trainers")
def list_trainers(db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    return db.query(Trainer).order_by(Trainer.name).all()


@router.post("/training/trainers", status_code=201)
def create_trainer(data: TrainerCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    require_record(db, User, data.user_id, "Trainer user")
    record = Trainer(**data.model_dump()); db.add(record); db.flush()
    audit(db, user, "trainer.created", "trainer", record.id); db.commit(); db.refresh(record)
    return record


@router.get("/training/batches")
def list_training_batches(course_id: int | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(TrainingBatch)
    if course_id: query = query.filter(TrainingBatch.course_id == course_id)
    if status: query = query.filter(TrainingBatch.status == status)
    return query.order_by(TrainingBatch.start_date.desc().nullslast()).limit(500).all()


@router.post("/training/batches", status_code=201)
def create_training_batch(data: TrainingBatchCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    require_record(db, Course, data.course_id, "Course"); require_record(db, Trainer, data.trainer_id, "Trainer")
    if data.start_date and data.end_date and data.end_date < data.start_date: raise HTTPException(422, "Batch end date cannot be before its start date")
    record = TrainingBatch(**data.model_dump()); db.add(record); db.flush()
    audit(db, user, "training_batch.created", "training_batch", record.id); db.commit(); db.refresh(record)
    return record


@router.patch("/training/batches/{batch_id}")
def update_training_batch(batch_id: int, data: TrainingBatchUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    record = require_record(db, TrainingBatch, batch_id, "Batch"); changes = data.model_dump(exclude_unset=True)
    require_record(db, Trainer, changes.get("trainer_id"), "Trainer")
    start = changes.get("start_date", record.start_date); end = changes.get("end_date", record.end_date)
    if start and end and end < start: raise HTTPException(422, "Batch end date cannot be before its start date")
    set_fields(record, changes); audit(db, user, "training_batch.updated", "training_batch", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/training/enrollments")
def list_enrollments(batch_id: int | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(Enrollment)
    if batch_id: query = query.filter(Enrollment.batch_id == batch_id)
    if status: query = query.filter(Enrollment.status == status)
    return query.order_by(Enrollment.enrolled_at.desc()).limit(1000).all()


@router.post("/training/enrollments", status_code=201)
def create_enrollment(data: EnrollmentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    require_record(db, TrainingBatch, data.batch_id, "Batch"); require_record(db, InternshipApplication, data.application_id, "Application")
    record = Enrollment(**{**data.model_dump(), "student_email": str(data.student_email).lower()})
    db.add(record); db.flush(); audit(db, user, "enrollment.created", "enrollment", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/training/enrollments/{enrollment_id}")
def update_enrollment(enrollment_id: int, data: EnrollmentUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    record = require_record(db, Enrollment, enrollment_id, "Enrollment"); changes = data.model_dump(exclude_unset=True)
    if changes.get("status") == "completed" and changes.get("completed_at") is None and record.completed_at is None: changes["completed_at"] = datetime.utcnow()
    set_fields(record, changes); audit(db, user, "enrollment.updated", "enrollment", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/training/sessions")
def list_training_sessions(batch_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(TrainingSession)
    if batch_id: query = query.filter(TrainingSession.batch_id == batch_id)
    return query.order_by(TrainingSession.starts_at.desc()).limit(500).all()


@router.post("/training/sessions", status_code=201)
def create_training_session(data: TrainingSessionCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    batch = require_record(db, TrainingBatch, data.batch_id, "Batch")
    if data.ends_at and data.ends_at < data.starts_at: raise HTTPException(422, "Session end time must be after its start time")
    record = TrainingSession(**data.model_dump()); db.add(record); db.flush()
    trainer = db.get(Trainer, batch.trainer_id) if batch.trainer_id else None
    if trainer and trainer.user_id and trainer.user_id != user.id:
        db.add(Notification(user_id=trainer.user_id, title="Training session scheduled", message=f"{data.title} is scheduled for {data.starts_at:%d %b %Y %H:%M}.", related_type="training_session", related_id=record.id))
    audit(db, user, "training_session.created", "training_session", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/training/attendance")
def list_training_attendance(session_id: int | None = None, enrollment_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(TrainingAttendance)
    if session_id: query = query.filter(TrainingAttendance.session_id == session_id)
    if enrollment_id: query = query.filter(TrainingAttendance.enrollment_id == enrollment_id)
    return query.order_by(TrainingAttendance.recorded_at.desc()).limit(1000).all()


@router.post("/training/attendance", status_code=201)
def record_training_attendance(data: TrainingAttendanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    require_record(db, TrainingSession, data.session_id, "Session"); require_record(db, Enrollment, data.enrollment_id, "Enrollment")
    existing = db.query(TrainingAttendance).filter_by(session_id=data.session_id, enrollment_id=data.enrollment_id).first()
    if existing: raise HTTPException(409, "Attendance is already recorded for this learner and session")
    record = TrainingAttendance(**data.model_dump(), recorded_by_id=user.id)
    db.add(record); db.flush(); audit(db, user, "training_attendance.recorded", "training_attendance", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/training/assessments")
def list_assessments(course_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(Assessment)
    if course_id: query = query.filter(Assessment.course_id == course_id)
    return query.order_by(Assessment.created_at.desc()).all()


@router.post("/training/assessments", status_code=201)
def create_assessment(data: AssessmentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    require_record(db, Course, data.course_id, "Course")
    record = Assessment(**data.model_dump()); db.add(record); db.flush(); audit(db, user, "assessment.created", "assessment", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/training/results")
def list_assessment_results(assessment_id: int | None = None, enrollment_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    query = db.query(AssessmentResult)
    if assessment_id: query = query.filter(AssessmentResult.assessment_id == assessment_id)
    if enrollment_id: query = query.filter(AssessmentResult.enrollment_id == enrollment_id)
    return query.order_by(AssessmentResult.submitted_at.desc().nullslast()).limit(1000).all()


@router.post("/training/results", status_code=201)
def create_assessment_result(data: AssessmentResultCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING))):
    assessment = require_record(db, Assessment, data.assessment_id, "Assessment"); require_record(db, Enrollment, data.enrollment_id, "Enrollment")
    if data.score > assessment.max_score: raise HTTPException(422, "Score cannot exceed the assessment maximum")
    if db.query(AssessmentResult).filter_by(assessment_id=data.assessment_id, enrollment_id=data.enrollment_id).first(): raise HTTPException(409, "A result is already recorded for this learner")
    record = AssessmentResult(**data.model_dump()); db.add(record); db.flush(); audit(db, user, "assessment_result.created", "assessment_result", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/training/feedback")
def list_learner_feedback(enrollment_id: int | None = None, application_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING, *INTERNSHIP))):
    query = db.query(LearnerFeedback)
    if enrollment_id: query = query.filter(LearnerFeedback.enrollment_id == enrollment_id)
    if application_id: query = query.filter(LearnerFeedback.application_id == application_id)
    return query.order_by(LearnerFeedback.created_at.desc()).limit(1000).all()


@router.post("/training/feedback", status_code=201)
def create_learner_feedback(data: LearnerFeedbackCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TRAINING, *INTERNSHIP))):
    if not data.enrollment_id and not data.application_id: raise HTTPException(422, "Link feedback to an enrollment or internship application")
    require_record(db, Enrollment, data.enrollment_id, "Enrollment"); require_record(db, InternshipApplication, data.application_id, "Application")
    record = LearnerFeedback(**data.model_dump()); db.add(record); db.flush(); audit(db, user, "learner_feedback.created", "learner_feedback", record.id)
    db.commit(); db.refresh(record)
    return record


# College and business partnerships
@router.get("/partners")
def list_partners(status: str | None = None, search: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    query = db.query(Partner)
    if status: query = query.filter(Partner.status == status)
    if search: query = query.filter(Partner.name.ilike(f"%{search}%"))
    return query.order_by(Partner.updated_at.desc()).limit(500).all()


@router.post("/partners", status_code=201)
def create_partner(data: PartnerCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Organization, data.organization_id, "Organization"); require_record(db, Contact, data.primary_contact_id, "Contact")
    record = Partner(**data.model_dump()); db.add(record); db.flush(); audit(db, user, "partner.created", "partner", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/partners/{partner_id}")
def update_partner(partner_id: int, data: PartnerUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    record = require_record(db, Partner, partner_id, "Partner"); changes = data.model_dump(exclude_unset=True)
    require_record(db, Organization, changes.get("organization_id"), "Organization"); require_record(db, Contact, changes.get("primary_contact_id"), "Contact")
    set_fields(record, changes); audit(db, user, "partner.updated", "partner", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/partners/{partner_id}/activities")
def list_partnership_activities(partner_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Partner, partner_id, "Partner")
    return db.query(PartnershipActivity).filter_by(partner_id=partner_id).order_by(PartnershipActivity.activity_date.desc().nullslast()).all()


@router.post("/partners/{partner_id}/activities", status_code=201)
def create_partnership_activity(partner_id: int, data: PartnershipActivityCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Partner, partner_id, "Partner")
    values = data.model_dump(exclude={"partner_id"}); record = PartnershipActivity(**values, partner_id=partner_id, owner_id=user.id)
    db.add(record); db.flush(); audit(db, user, "partnership_activity.created", "partnership_activity", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/partners/{partner_id}/agreements")
def list_partnership_agreements(partner_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Partner, partner_id, "Partner")
    return db.query(PartnershipAgreement).filter_by(partner_id=partner_id).order_by(PartnershipAgreement.end_date.asc().nullslast()).all()


@router.post("/partners/{partner_id}/agreements", status_code=201)
def create_partnership_agreement(partner_id: int, data: PartnershipAgreementCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Partner, partner_id, "Partner")
    if data.start_date and data.end_date and data.end_date < data.start_date: raise HTTPException(422, "Agreement end date cannot precede its start date")
    record = PartnershipAgreement(**data.model_dump(exclude={"partner_id"}), partner_id=partner_id)
    db.add(record); db.flush(); audit(db, user, "partnership_agreement.created", "partnership_agreement", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/partners/{partner_id}/agreements/{agreement_id}")
def update_partnership_agreement(partner_id: int, agreement_id: int, data: PartnershipAgreementUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    require_record(db, Partner, partner_id, "Partner")
    record = db.query(PartnershipAgreement).filter_by(id=agreement_id, partner_id=partner_id).first()
    if not record: raise HTTPException(404, "Agreement not found")
    changes = data.model_dump(exclude_unset=True); start = changes.get("start_date", record.start_date); end = changes.get("end_date", record.end_date)
    if start and end and end < start: raise HTTPException(422, "Agreement end date cannot precede its start date")
    set_fields(record, changes); audit(db, user, "partnership_agreement.updated", "partnership_agreement", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/partnership-activities")
def list_all_partnership_activities(partner_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    query = db.query(PartnershipActivity)
    if partner_id: query = query.filter(PartnershipActivity.partner_id == partner_id)
    return query.order_by(PartnershipActivity.created_at.desc()).limit(1000).all()


@router.post("/partnership-activities", status_code=201)
def create_all_partnership_activity(data: PartnershipActivityCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    return create_partnership_activity(data.partner_id, data, db, user)


@router.get("/partnership-agreements")
def list_all_partnership_agreements(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    query = db.query(PartnershipAgreement)
    if status: query = query.filter(PartnershipAgreement.status == status)
    return query.order_by(PartnershipAgreement.end_date.asc().nullslast()).limit(1000).all()


@router.post("/partnership-agreements", status_code=201)
def create_all_partnership_agreement(data: PartnershipAgreementCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    return create_partnership_agreement(data.partner_id, data, db, user)


@router.patch("/partnership-agreements/{agreement_id}")
def update_all_partnership_agreement(agreement_id: int, data: PartnershipAgreementUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PARTNERSHIPS))):
    record = require_record(db, PartnershipAgreement, agreement_id, "Agreement")
    changes = data.model_dump(exclude_unset=True)
    start = changes.get("start_date", record.start_date); end = changes.get("end_date", record.end_date)
    if start and end and end < start: raise HTTPException(422, "Agreement end date cannot precede its start date")
    set_fields(record, changes); audit(db, user, "partnership_agreement.updated", "partnership_agreement", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


# Client delivery, projects, milestone history and project tasks
@router.get("/projects")
def list_projects(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    query = db.query(Project)
    if not {role.name for role in user.roles}.intersection(MANAGEMENT):
        query = query.filter(Project.project_manager_id == user.id)
    if status: query = query.filter(Project.status == status)
    return query.order_by(Project.updated_at.desc()).limit(500).all()


@router.post("/projects", status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_record(db, Organization, data.organization_id, "Organization")
    roles = {role.name for role in user.roles}
    if not roles.intersection(MANAGEMENT) and data.project_manager_id not in (None, user.id):
        raise HTTPException(403, "Only management can assign a project to another manager")
    manager_id = data.project_manager_id or user.id; require_record(db, User, manager_id, "Project manager")
    values = data.model_dump(); values["project_manager_id"] = manager_id
    record = Project(**values); db.add(record); db.flush(); audit(db, user, "project.created", "project", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/projects/{project_id}")
def update_project(project_id: int, data: ProjectPatch, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    record = require_project(db, project_id, user); changes = data.model_dump(exclude_unset=True)
    if "project_manager_id" in changes and not {role.name for role in user.roles}.intersection(MANAGEMENT):
        raise HTTPException(403, "Only management can reassign project managers")
    require_record(db, Organization, changes.get("organization_id"), "Organization"); require_record(db, User, changes.get("project_manager_id"), "Project manager")
    set_fields(record, changes); audit(db, user, "project.updated", "project", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/projects/{project_id}/milestones")
def list_project_milestones(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    return db.query(ProjectMilestone).filter_by(project_id=project_id).order_by(ProjectMilestone.due_date.asc().nullslast()).all()


@router.post("/projects/{project_id}/milestones", status_code=201)
def create_project_milestone(project_id: int, data: MilestoneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    record = ProjectMilestone(**data.model_dump(exclude={"project_id"}), project_id=project_id)
    if record.status == "completed": record.completed_at = datetime.utcnow()
    db.add(record); db.flush(); audit(db, user, "project_milestone.created", "project_milestone", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/projects/{project_id}/milestones/{milestone_id}")
def update_project_milestone(project_id: int, milestone_id: int, data: MilestoneUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    record = db.query(ProjectMilestone).filter_by(id=milestone_id, project_id=project_id).first()
    if not record: raise HTTPException(404, "Milestone not found")
    changes = data.model_dump(exclude_unset=True); set_fields(record, changes)
    if record.status == "completed" and not record.completed_at: record.completed_at = datetime.utcnow()
    if record.status != "completed": record.completed_at = None
    audit(db, user, "project_milestone.updated", "project_milestone", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/projects/{project_id}/updates")
def list_project_updates(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    return db.query(ProjectUpdate).filter_by(project_id=project_id).order_by(ProjectUpdate.created_at.desc()).limit(500).all()


@router.post("/projects/{project_id}/updates", status_code=201)
def create_project_update(project_id: int, data: ProjectUpdateCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    record = ProjectUpdate(**data.model_dump(exclude={"project_id"}), project_id=project_id, author_id=user.id)
    db.add(record); db.flush(); audit(db, user, "project_update.created", "project_update", record.id)
    db.commit(); db.refresh(record)
    return record


@router.get("/projects/{project_id}/tasks")
def list_project_tasks(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    return db.query(ProjectTask).filter_by(project_id=project_id).order_by(ProjectTask.due_at.asc().nullslast()).all()


@router.post("/projects/{project_id}/tasks", status_code=201)
def create_project_task(project_id: int, data: ProjectTaskCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user); require_record(db, User, data.assignee_id, "Assignee")
    values = data.model_dump(); values["created_by_id"] = user.id
    if values.get("assignee_id") is None: values["assignee_id"] = user.id
    values.pop("project_id", None)
    record = ProjectTask(**values, project_id=project_id); db.add(record); db.flush()
    if record.assignee_id != user.id:
        db.add(Notification(user_id=record.assignee_id, title="Project task assigned", message=f"You were assigned: {record.title}", related_type="project", related_id=project_id))
    audit(db, user, "project_task.created", "project_task", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/projects/{project_id}/tasks/{task_id}")
def update_project_task(project_id: int, task_id: int, data: ProjectTaskUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    require_project(db, project_id, user)
    record = db.query(ProjectTask).filter_by(id=task_id, project_id=project_id).first()
    if not record: raise HTTPException(404, "Project task not found")
    changes = data.model_dump(exclude_unset=True); require_record(db, User, changes.get("assignee_id"), "Assignee")
    set_fields(record, changes); audit(db, user, "project_task.updated", "project_task", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/project-milestones")
def list_all_project_milestones(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    query = db.query(ProjectMilestone)
    if project_id:
        require_project(db, project_id, user); query = query.filter(ProjectMilestone.project_id == project_id)
    elif not {role.name for role in user.roles}.intersection(MANAGEMENT):
        query = query.join(Project, ProjectMilestone.project_id == Project.id).filter(Project.project_manager_id == user.id)
    return query.order_by(ProjectMilestone.due_date.asc().nullslast()).limit(1000).all()


@router.post("/project-milestones", status_code=201)
def create_all_project_milestone(data: MilestoneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    if not data.project_id: raise HTTPException(422, "Project ID is required")
    return create_project_milestone(data.project_id, data, db, user)


@router.patch("/project-milestones/{milestone_id}")
def update_all_project_milestone(milestone_id: int, data: MilestoneUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    record = require_record(db, ProjectMilestone, milestone_id, "Milestone"); changes = data.model_dump(exclude_unset=True)
    require_project(db, record.project_id, user)
    set_fields(record, changes)
    if record.status == "completed" and not record.completed_at: record.completed_at = datetime.utcnow()
    if record.status != "completed": record.completed_at = None
    audit(db, user, "project_milestone.updated", "project_milestone", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


@router.get("/project-updates")
def list_all_project_updates(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    query = db.query(ProjectUpdate)
    if project_id:
        require_project(db, project_id, user); query = query.filter(ProjectUpdate.project_id == project_id)
    elif not {role.name for role in user.roles}.intersection(MANAGEMENT):
        query = query.join(Project, ProjectUpdate.project_id == Project.id).filter(Project.project_manager_id == user.id)
    return query.order_by(ProjectUpdate.created_at.desc()).limit(1000).all()


@router.post("/project-updates", status_code=201)
def create_all_project_update(data: ProjectUpdateCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    if not data.project_id: raise HTTPException(422, "Project ID is required")
    return create_project_update(data.project_id, data, db, user)


@router.get("/project-tasks")
def list_all_project_tasks(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(ProjectTask)
    roles = {role.name for role in user.roles}
    if roles.intersection(PROJECTS):
        if not roles.intersection(MANAGEMENT): query = query.join(Project, ProjectTask.project_id == Project.id).filter(Project.project_manager_id == user.id)
    else:
        query = query.filter(ProjectTask.assignee_id == user.id)
    if status: query = query.filter(ProjectTask.status == status)
    return query.order_by(ProjectTask.due_at.asc().nullslast()).limit(1000).all()


@router.post("/project-tasks", status_code=201)
def create_all_project_task(data: ProjectTaskCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*PROJECTS))):
    if not data.project_id: raise HTTPException(422, "Project ID is required")
    return create_project_task(data.project_id, data, db, user)


@router.patch("/project-tasks/{task_id}")
def update_all_project_task(task_id: int, data: ProjectTaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = require_record(db, ProjectTask, task_id, "Project task")
    roles = {role.name for role in user.roles}
    if roles.intersection(PROJECTS): require_project(db, record.project_id, user)
    if record.assignee_id != user.id and not roles.intersection(PROJECTS): raise HTTPException(403, "Not permitted to update this task")
    changes = data.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        require_record(db, User, changes["assignee_id"], "Assignee")
        if not roles.intersection(PROJECTS): raise HTTPException(403, "Only a project manager can reassign tasks")
    set_fields(record, changes); audit(db, user, "project_task.updated", "project_task", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record


# In-app notifications. Email and external messaging are intentionally not sent here.
@router.get("/notifications")
def list_notifications(unread_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only: query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).limit(100).all()


@router.post("/notifications", status_code=201)
def create_notification(data: NotificationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT))):
    require_record(db, User, data.user_id, "User")
    record = Notification(**data.model_dump(), status="pending", channel="in_app")
    db.add(record); db.flush(); audit(db, user, "notification.created", "notification", record.id)
    db.commit(); db.refresh(record)
    return record


@router.post("/notifications/refresh-reminders")
def refresh_reminders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    overdue_tasks = db.query(Task).filter(Task.assignee_id == user.id, Task.due_at < now, Task.status.notin_(["done", "cancelled"])).limit(100).all()
    due_leads = db.query(Lead).filter(Lead.owner_id == user.id, Lead.next_follow_up_at <= now, Lead.status.notin_(["converted", "lost"])).limit(100).all()
    added = 0
    for task in overdue_tasks:
        exists = db.query(Notification.id).filter_by(user_id=user.id, related_type="task_overdue", related_id=task.id).first()
        if not exists:
            db.add(Notification(user_id=user.id, title="Task overdue", message=f"{task.title} is past its due date.", related_type="task_overdue", related_id=task.id)); added += 1
    for lead in due_leads:
        exists = db.query(Notification.id).filter_by(user_id=user.id, related_type="lead_followup", related_id=lead.id).first()
        if not exists:
            db.add(Notification(user_id=user.id, title="Lead follow-up due", message=f"Follow up with {lead.first_name} {lead.last_name or ''}".strip(), related_type="lead_followup", related_id=lead.id)); added += 1
    db.commit()
    return {"created": added}


@router.patch("/notifications/{notification_id}")
def update_notification(notification_id: int, data: NotificationRead, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not record: raise HTTPException(404, "Notification not found")
    record.read_at = datetime.utcnow() if data.is_read else None
    record.status = "read" if data.is_read else "pending"
    db.commit(); db.refresh(record)
    return record


# Role-aware dashboards, controlled exports and administration
@router.get("/reports/summary")
def report_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    roles = {role.name for role in user.roles}
    all_business = bool(roles.intersection(MANAGEMENT))
    lead_query = db.query(Lead)
    opportunity_query = db.query(Opportunity)
    application_query = db.query(InternshipApplication)
    enrollment_query = db.query(Enrollment)
    task_query = db.query(Task)
    project_query = db.query(Project)
    if not all_business:
        lead_query = lead_query.filter(Lead.owner_id == user.id)
        opportunity_query = opportunity_query.filter(Opportunity.owner_id == user.id)
        application_query = application_query.filter(InternshipApplication.coordinator_id == user.id)
        enrollment_query = enrollment_query.filter(Enrollment.id < 0)
        task_query = task_query.filter(or_(Task.assignee_id == user.id, Task.created_by_id == user.id))
        project_query = project_query.filter(Project.project_manager_id == user.id)
    finance_allowed = bool(roles.intersection(FINANCE))
    return {
        "leads_total": lead_query.count(),
        "leads_with_next_action": lead_query.filter(Lead.next_follow_up_at.is_not(None)).count(),
        "opportunities_open": opportunity_query.filter(Opportunity.stage.notin_(["won", "lost"])).count(),
        "pipeline_value": str(opportunity_query.filter(Opportunity.stage.notin_(["won", "lost"])).with_entities(func.coalesce(func.sum(Opportunity.expected_value), 0)).scalar()),
        "applications_active": application_query.filter(InternshipApplication.status.notin_(["completed", "rejected", "withdrawn"])).count(),
        "applications_completed": application_query.filter(InternshipApplication.status == "completed").count(),
        "training_enrollments": enrollment_query.count(),
        "tasks_overdue": task_query.filter(Task.due_at < datetime.utcnow(), Task.status.notin_(["done", "cancelled"])).count(),
        "projects_active": project_query.filter(Project.status == "active").count(),
        "finance_visible": finance_allowed,
        "invoiced_amount": str(db.query(func.coalesce(func.sum(Invoice.amount), 0)).scalar()) if finance_allowed else None,
        "payments_received": str(db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(PaymentTransaction.status == "received").scalar()) if finance_allowed else None,
    }


@router.get("/reports/export/{dataset}")
def export_csv(dataset: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    roles = {role.name for role in user.roles}
    exports = {
        "leads": (Lead, ("id", "first_name", "last_name", "email", "phone", "organization_name", "source", "interest", "status", "priority", "owner_id", "next_follow_up_at"), SALES),
        "opportunities": (Opportunity, ("id", "name", "stage", "expected_value", "expected_close_date", "owner_id", "organization_id"), SALES),
        "applications": (InternshipApplication, ("id", "full_name", "email", "college_name", "status", "program_id", "coordinator_id", "applied_at"), INTERNSHIP),
        "enrollments": (Enrollment, ("id", "student_name", "student_email", "batch_id", "status", "enrolled_at", "completed_at"), TRAINING),
        "projects": (Project, ("id", "name", "status", "organization_id", "project_manager_id", "start_date", "target_end_date"), PROJECTS),
    }
    if dataset == "invoices":
        if not roles.intersection(FINANCE): raise HTTPException(403, "Finance role required for invoice exports")
        model, fields = Invoice, ("id", "invoice_number", "description", "amount", "due_date", "status", "organization_id", "opportunity_id")
    elif dataset in exports:
        model, fields, allowed = exports[dataset]
        if not roles.intersection(allowed): raise HTTPException(403, "Your role cannot export this dataset")
    else:
        raise HTTPException(404, "Export dataset not found")
    query = db.query(model)
    if dataset == "leads" and not roles.intersection(MANAGEMENT): query = query.filter(Lead.owner_id == user.id)
    if dataset == "opportunities" and not roles.intersection(MANAGEMENT): query = query.filter(Opportunity.owner_id == user.id)
    if dataset == "applications" and "Super Admin" not in roles and "Management" not in roles: query = query.filter(InternshipApplication.coordinator_id == user.id)
    if dataset == "projects" and "Super Admin" not in roles and "Management" not in roles: query = query.filter(Project.project_manager_id == user.id)
    output = StringIO(newline="")
    writer = csv.writer(output); writer.writerow(fields)
    for row in query.limit(10000).all(): writer.writerow([getattr(row, field) for field in fields])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=hruta-{dataset}.csv"})


@router.get("/admin/users")
def list_users(search: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    query = db.query(User)
    if search:
        like = f"%{search}%"; query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))
    return [{"id": person.id, "full_name": person.full_name, "email": person.email, "is_active": person.is_active, "roles": [role.name for role in person.roles]} for person in query.order_by(User.full_name).limit(500).all()]


@router.get("/admin/roles")
def list_roles(db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    return db.query(Role).order_by(Role.name).all()


@router.patch("/admin/users/{user_id}/roles")
def update_user_roles(user_id: int, data: RoleAssignment, db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    target = require_record(db, User, user_id, "User")
    roles = db.query(Role).filter(Role.name.in_(data.role_names)).all()
    found = {role.name for role in roles}
    if found != set(data.role_names): raise HTTPException(422, f"Unknown role(s): {', '.join(sorted(set(data.role_names) - found))}")
    removes_admin = "Super Admin" in {role.name for role in target.roles} and "Super Admin" not in found
    if removes_admin:
        other_admins = db.query(User).join(User.roles).filter(Role.name == "Super Admin", User.is_active.is_(True), User.id != target.id).count()
        if not other_admins: raise HTTPException(409, "At least one active Super Admin must remain")
    target.roles = roles
    if data.is_active is not None: target.is_active = data.is_active
    audit(db, user, "user.roles_updated", "user", target.id, ",".join(sorted(found)))
    db.commit(); db.refresh(target)
    return {"id": target.id, "full_name": target.full_name, "email": target.email, "is_active": target.is_active, "roles": [role.name for role in target.roles]}


@router.get("/admin/audit-logs")
def list_audit_logs(entity_type: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    query = db.query(AuditLog)
    if entity_type: query = query.filter(AuditLog.entity_type == entity_type)
    return query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


@router.get("/admin/configuration")
def list_configuration(db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    return db.query(AppConfiguration).order_by(AppConfiguration.key).all()


@router.put("/admin/configuration/{key}")
def update_configuration(key: str, data: ConfigurationUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SUPER_ADMIN))):
    record = db.get(AppConfiguration, key)
    if record is None:
        record = AppConfiguration(key=key, value=data.value, description=data.description, updated_by_id=user.id)
        db.add(record)
    else:
        record.value = data.value; record.description = data.description; record.updated_by_id = user.id
    audit(db, user, "configuration.updated", "configuration", key)
    db.commit(); db.refresh(record)
    return record


@router.get("/sales/proposals")
def list_sales_proposals(opportunity_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    query = db.query(SalesProposal)
    if opportunity_id: query = query.filter(SalesProposal.opportunity_id == opportunity_id)
    roles = {role.name for role in user.roles}
    if not roles.intersection(MANAGEMENT):
        query = query.join(Opportunity, SalesProposal.opportunity_id == Opportunity.id).filter(Opportunity.owner_id == user.id)
    return query.order_by(SalesProposal.created_at.desc()).limit(500).all()


@router.post("/sales/proposals", status_code=201)
def create_sales_proposal(data: SalesProposalCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    opportunity = require_record(db, Opportunity, data.opportunity_id, "Opportunity")
    roles = {role.name for role in user.roles}
    if opportunity.owner_id != user.id and not roles.intersection(MANAGEMENT): raise HTTPException(403, "You can only create proposals for your own opportunities")
    record = SalesProposal(**data.model_dump(), created_by_id=user.id)
    db.add(record); db.flush()
    if data.status == "sent": opportunity.stage = "proposal"
    audit(db, user, "sales_proposal.created", "sales_proposal", record.id)
    db.commit(); db.refresh(record)
    return record


@router.patch("/sales/proposals/{proposal_id}")
def update_sales_proposal(proposal_id: int, data: SalesProposalUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    record = require_record(db, SalesProposal, proposal_id, "Proposal")
    opportunity = require_record(db, Opportunity, record.opportunity_id, "Opportunity")
    roles = {role.name for role in user.roles}
    if opportunity.owner_id != user.id and not roles.intersection(MANAGEMENT): raise HTTPException(403, "You can only update proposals for your own opportunities")
    changes = data.model_dump(exclude_unset=True); set_fields(record, changes)
    if record.status == "sent" and not record.sent_at: record.sent_at = datetime.utcnow()
    audit(db, user, "sales_proposal.updated", "sales_proposal", record.id, ",".join(changes))
    db.commit(); db.refresh(record)
    return record

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecordModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InternshipProgramCreate(RecordModel):
    name: str = Field(min_length=2, max_length=200)
    domain: str | None = Field(default=None, max_length=120)
    description: str | None = None
    duration_weeks: int | None = Field(default=None, gt=0)
    mode: Literal["online", "onsite", "hybrid"] | None = None
    fee: Decimal = Field(default=Decimal("0"), ge=0)


class InternshipProgramUpdate(RecordModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    domain: str | None = None
    description: str | None = None
    duration_weeks: int | None = Field(default=None, gt=0)
    mode: Literal["online", "onsite", "hybrid"] | None = None
    fee: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class InternshipApplicationCreate(RecordModel):
    program_id: int | None = None
    lead_id: int | None = None
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = None
    college_name: str | None = None
    coordinator_id: int | None = None
    status: Literal["applied", "interview_scheduled", "selected", "offered", "onboarding", "active", "completed", "rejected", "withdrawn"] = "applied"
    start_date: date | None = None
    end_date: date | None = None
    team_name: str | None = None
    notes: str | None = None


class InternshipApplicationUpdate(RecordModel):
    program_id: int | None = None
    coordinator_id: int | None = None
    status: Literal["applied", "interview_scheduled", "selected", "offered", "onboarding", "active", "completed", "rejected", "withdrawn"] | None = None
    start_date: date | None = None
    end_date: date | None = None
    team_name: str | None = None
    notes: str | None = None


class InterviewCreate(RecordModel):
    application_id: int
    interviewer_id: int | None = None
    scheduled_at: datetime
    status: Literal["scheduled", "completed", "cancelled", "no_show"] = "scheduled"
    feedback: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


class InterviewUpdate(RecordModel):
    interviewer_id: int | None = None
    scheduled_at: datetime | None = None
    status: Literal["scheduled", "completed", "cancelled", "no_show"] | None = None
    feedback: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


class InternAllocationCreate(RecordModel):
    application_id: int
    team_name: str = Field(min_length=2, max_length=120)
    coordinator_id: int | None = None
    notes: str | None = None


class InternshipAttendanceCreate(RecordModel):
    application_id: int
    attendance_date: date
    status: Literal["present", "absent", "leave"]
    notes: str | None = None


class InternshipTaskCreate(RecordModel):
    application_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    due_date: date | None = None


class InternshipTaskUpdate(RecordModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: Literal["assigned", "in_progress", "submitted", "reviewed", "completed"] | None = None
    feedback: str | None = None


class CertificateCreate(RecordModel):
    application_id: int
    certificate_type: Literal["completion", "experience", "other"]
    certificate_number: str | None = Field(default=None, max_length=100)
    storage_key: str | None = Field(default=None, max_length=500)


class CertificateUpdate(RecordModel):
    status: Literal["pending", "approved", "issued", "cancelled"] | None = None
    certificate_number: str | None = Field(default=None, max_length=100)
    storage_key: str | None = Field(default=None, max_length=500)


class CourseCreate(RecordModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    syllabus_reference: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(default=Decimal("0"), ge=0)


class CourseUpdate(RecordModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    syllabus_reference: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class TrainerCreate(RecordModel):
    user_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    expertise: str | None = None


class TrainingBatchCreate(RecordModel):
    course_id: int
    trainer_id: int | None = None
    name: str = Field(min_length=2, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    mode: Literal["online", "onsite", "hybrid"] | None = None
    status: Literal["planned", "active", "completed", "cancelled"] = "planned"


class TrainingBatchUpdate(RecordModel):
    trainer_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    mode: Literal["online", "onsite", "hybrid"] | None = None
    status: Literal["planned", "active", "completed", "cancelled"] | None = None


class EnrollmentCreate(RecordModel):
    batch_id: int
    application_id: int | None = None
    student_name: str = Field(min_length=2, max_length=200)
    student_email: EmailStr


class EnrollmentUpdate(RecordModel):
    status: Literal["enrolled", "in_progress", "completed", "withdrawn"] | None = None
    completed_at: datetime | None = None


class TrainingSessionCreate(RecordModel):
    batch_id: int
    title: str = Field(min_length=2, max_length=200)
    starts_at: datetime
    ends_at: datetime | None = None
    meeting_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = None


class TrainingAttendanceCreate(RecordModel):
    session_id: int
    enrollment_id: int
    status: Literal["present", "absent", "late", "excused"]


class AssessmentCreate(RecordModel):
    course_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    max_score: Decimal = Field(default=Decimal("100"), gt=0)


class AssessmentResultCreate(RecordModel):
    assessment_id: int
    enrollment_id: int
    score: Decimal = Field(ge=0)
    feedback: str | None = None
    submitted_at: datetime | None = None


class LearnerFeedbackCreate(RecordModel):
    enrollment_id: int | None = None
    application_id: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    comments: str | None = None


class PartnerCreate(RecordModel):
    organization_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    partner_type: str = Field(default="college", max_length=40)
    primary_contact_id: int | None = None
    status: Literal["prospect", "active", "inactive", "expired"] = "prospect"
    notes: str | None = None


class PartnerUpdate(RecordModel):
    organization_id: int | None = None
    primary_contact_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    partner_type: str | None = Field(default=None, max_length=40)
    status: Literal["prospect", "active", "inactive", "expired"] | None = None
    notes: str | None = None


class PartnershipActivityCreate(RecordModel):
    partner_id: int
    activity_type: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    activity_date: date | None = None


class PartnershipAgreementCreate(RecordModel):
    partner_id: int
    title: str = Field(min_length=2, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["draft", "active", "renewal_due", "expired", "terminated"] = "draft"
    storage_key: str | None = Field(default=None, max_length=500)


class PartnershipAgreementUpdate(RecordModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["draft", "active", "renewal_due", "expired", "terminated"] | None = None
    storage_key: str | None = Field(default=None, max_length=500)


class ProjectCreate(RecordModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    organization_id: int | None = None
    project_manager_id: int | None = None
    status: Literal["planned", "active", "on_hold", "completed", "cancelled"] = "planned"
    start_date: date | None = None
    target_end_date: date | None = None


class ProjectUpdate(RecordModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    organization_id: int | None = None
    project_manager_id: int | None = None
    status: Literal["planned", "active", "on_hold", "completed", "cancelled"] | None = None
    start_date: date | None = None
    target_end_date: date | None = None


class MilestoneCreate(RecordModel):
    project_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: Literal["pending", "in_progress", "completed", "delayed"] = "pending"


class MilestoneUpdate(RecordModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: Literal["pending", "in_progress", "completed", "delayed"] | None = None


class ProjectUpdateCreate(RecordModel):
    project_id: int | None = None
    update_text: str = Field(min_length=2)
    progress_percent: int | None = Field(default=None, ge=0, le=100)


class ProjectTaskCreate(RecordModel):
    project_id: int | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class ProjectTaskUpdate(RecordModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] | None = None
    status: Literal["todo", "in_progress", "blocked", "done", "cancelled"] | None = None


class NotificationCreate(RecordModel):
    user_id: int
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=2)
    related_type: str | None = Field(default=None, max_length=60)
    related_id: int | None = None


class NotificationRead(RecordModel):
    is_read: bool = True


class RefundCreate(RecordModel):
    payment_id: int
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=3)


class RefundDecision(RecordModel):
    reason: str | None = None


class RoleAssignment(RecordModel):
    role_names: list[str] = Field(min_length=1)
    is_active: bool | None = None


class ConfigurationUpdate(RecordModel):
    value: dict
    description: str | None = None


class SalesProposalCreate(RecordModel):
    opportunity_id: int
    title: str = Field(min_length=2, max_length=200)
    version: int = Field(default=1, ge=1)
    amount: Decimal | None = Field(default=None, ge=0)
    status: Literal["draft", "sent", "accepted", "rejected"] = "draft"
    sent_at: datetime | None = None
    response_notes: str | None = None


class SalesProposalUpdate(RecordModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    version: int | None = Field(default=None, ge=1)
    amount: Decimal | None = Field(default=None, ge=0)
    status: Literal["draft", "sent", "accepted", "rejected"] | None = None
    sent_at: datetime | None = None
    response_notes: str | None = None

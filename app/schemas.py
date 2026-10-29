from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    roles: list[str] = []
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LeadCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    organization_name: str | None = None
    source: str = "manual"
    interest: str
    priority: str = "medium"
    status: str = "new"
    notes: str | None = None
    next_follow_up_at: datetime | None = None
    owner_id: int | None = None

class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    organization_name: str | None = None
    source: str | None = None
    interest: str | None = None
    priority: str | None = None
    status: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None
    owner_id: int | None = None

class LeadOut(BaseModel):
    id: int
    first_name: str
    last_name: str | None
    email: str | None
    phone: str | None
    organization_name: str | None
    source: str
    interest: str
    priority: str
    status: str
    notes: str | None
    next_follow_up_at: datetime | None
    owner_id: int | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    organization_type: str = "client"
    website: str | None = None
    industry: str | None = None
    address: str | None = None
    notes: str | None = None

class ContactCreate(BaseModel):
    organization_id: int | None = None
    first_name: str
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    designation: str | None = None

class OpportunityCreate(BaseModel):
    name: str
    lead_id: int | None = None
    organization_id: int | None = None
    contact_id: int | None = None
    stage: str = "qualification"
    expected_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    expected_close_date: date | None = None
    owner_id: int | None = None

class OpportunityUpdate(BaseModel):
    name: str | None = None
    lead_id: int | None = None
    organization_id: int | None = None
    contact_id: int | None = None
    stage: str | None = None
    expected_value: Decimal | None = Field(default=None, ge=0)
    expected_close_date: date | None = None
    lost_reason: str | None = None
    owner_id: int | None = None

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    status: str = "todo"
    due_at: datetime | None = None
    assignee_id: int | None = None
    lead_id: int | None = None
    opportunity_id: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    due_at: datetime | None = None
    assignee_id: int | None = None

class ActivityCreate(BaseModel):
    lead_id: int | None = None
    opportunity_id: int | None = None
    contact_id: int | None = None
    activity_type: str
    subject: str
    outcome: str | None = None
    notes: str | None = None
    occurred_at: datetime | None = None

class InvoiceCreate(BaseModel):
    invoice_number: str
    organization_id: int | None = None
    opportunity_id: int | None = None
    description: str
    amount: Decimal = Field(gt=0)
    due_date: date | None = None

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)
    payment_date: date | None = None
    method: str
    reference: str | None = None

from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (User, Lead, Organization, Contact, Opportunity, Activity, Task,
                      AuditLog, PipelineHistory, Notification, InternshipApplication,
                      Enrollment, TrainingBatch, Partner, Project, ProjectMilestone,
                      Invoice, PaymentTransaction, Refund)
from ..schemas import (LeadCreate, LeadUpdate, LeadOut, OrganizationCreate, ContactCreate,
                       OpportunityCreate, OpportunityUpdate, TaskCreate, TaskUpdate, ActivityCreate)
from ..security import get_current_user, require_roles

router = APIRouter(tags=["CRM"])
ADMIN = ("Super Admin",)
SALES = ("Super Admin", "Management", "Sales / Business Development")
TASK_ROLES = ("Super Admin", "Management", "Sales / Business Development", "Internship Coordinator", "Training Coordinator", "Project / Team Manager", "Employee / Intern")

def audit(db: Session, user: User, action: str, kind: str, entity_id: int, details: str | None = None):
    db.add(AuditLog(user_id=user.id, action=action, entity_type=kind, entity_id=str(entity_id), details=details))

@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(data: LeadCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    values = data.model_dump()
    roles = {r.name for r in user.roles}
    if not roles.intersection({"Super Admin", "Management"}) and values.get("owner_id") not in (None, user.id):
        raise HTTPException(403, "Only managers can assign a lead to another owner")
    if values.get("owner_id") is None or not roles.intersection({"Super Admin", "Management"}): values["owner_id"] = user.id
    possible_duplicate = None
    if values.get("email"):
        possible_duplicate = db.query(Lead).filter(Lead.email.ilike(str(values["email"]))).first()
    if not possible_duplicate and values.get("phone"):
        possible_duplicate = db.query(Lead).filter(Lead.phone == values["phone"]).first()
    if possible_duplicate:
        raise HTTPException(409, f"Possible duplicate lead detected (lead #{possible_duplicate.id})")
    lead = Lead(**values)
    db.add(lead); db.flush(); audit(db, user, "lead.created", "lead", lead.id); db.commit(); db.refresh(lead)
    return lead

@router.get("/leads", response_model=list[LeadOut])
def list_leads(search: str | None = None, status: str | None = None, interest: str | None = None,
               owner_id: int | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Lead)
    roles = {r.name for r in user.roles}
    if not roles.intersection({"Super Admin", "Management"}): q = q.filter(Lead.owner_id == user.id)
    if search: q = q.filter(or_(Lead.first_name.ilike(f"%{search}%"), Lead.last_name.ilike(f"%{search}%"), Lead.email.ilike(f"%{search}%"), Lead.organization_name.ilike(f"%{search}%"), Lead.phone.ilike(f"%{search}%")))
    if status: q = q.filter(Lead.status == status)
    if interest: q = q.filter(Lead.interest == interest)
    if owner_id and roles.intersection({"Super Admin", "Management"}): q = q.filter(Lead.owner_id == owner_id)
    return q.order_by(Lead.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()

@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead: raise HTTPException(404, "Lead not found")
    roles = {r.name for r in user.roles}
    if lead.owner_id != user.id and not roles.intersection({"Super Admin", "Management"}): raise HTTPException(403, "Not permitted to view this lead")
    return lead

@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    lead = db.get(Lead, lead_id)
    if not lead: raise HTTPException(404, "Lead not found")
    roles = {r.name for r in user.roles}
    if lead.owner_id != user.id and not roles.intersection({"Super Admin", "Management"}): raise HTTPException(403, "Not permitted to update this lead")
    changes = data.model_dump(exclude_unset=True)
    if "owner_id" in changes and not roles.intersection({"Super Admin", "Management"}):
        raise HTTPException(403, "Only managers can reassign leads")
    for key, value in changes.items(): setattr(lead, key, value)
    audit(db, user, "lead.updated", "lead", lead.id, ",".join(changes.keys())); db.commit(); db.refresh(lead)
    return lead

@router.post("/organizations", status_code=201)
def create_organization(data: OrganizationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    obj = Organization(**data.model_dump()); db.add(obj); db.flush(); audit(db,user,"organization.created","organization",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/organizations")
def list_organizations(search: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Organization)
    if search: q = q.filter(Organization.name.ilike(f"%{search}%"))
    return q.order_by(Organization.name).offset((page-1)*page_size).limit(page_size).all()

@router.post("/contacts", status_code=201)
def create_contact(data: ContactCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    if data.organization_id and not db.get(Organization, data.organization_id): raise HTTPException(404, "Organization not found")
    obj = Contact(**data.model_dump()); db.add(obj); db.flush(); audit(db,user,"contact.created","contact",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/contacts")
def list_contacts(search: str | None = None, organization_id: int | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Contact)
    if search: q = q.filter(or_(Contact.first_name.ilike(f"%{search}%"), Contact.last_name.ilike(f"%{search}%"), Contact.email.ilike(f"%{search}%"), Contact.phone.ilike(f"%{search}%")))
    if organization_id: q = q.filter(Contact.organization_id == organization_id)
    return q.order_by(Contact.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()

@router.post("/opportunities", status_code=201)
def create_opportunity(data: OpportunityCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    values = data.model_dump()
    roles = {r.name for r in user.roles}
    if not roles.intersection({"Super Admin", "Management"}) and values.get("owner_id") not in (None, user.id):
        raise HTTPException(403, "Only managers can assign an opportunity to another owner")
    if values.get("owner_id") is None or not roles.intersection({"Super Admin", "Management"}): values["owner_id"] = user.id
    for model, field, label in ((Lead, "lead_id", "Lead"), (Organization, "organization_id", "Organization"), (Contact, "contact_id", "Contact")):
        if values.get(field) and not db.get(model, values[field]): raise HTTPException(404, f"{label} not found")
    obj = Opportunity(**values); db.add(obj); db.flush()
    db.add(PipelineHistory(opportunity_id=obj.id, to_stage=obj.stage, changed_by_id=user.id))
    audit(db,user,"opportunity.created","opportunity",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/opportunities")
def list_opportunities(stage: str | None = None, owner_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Opportunity); roles = {r.name for r in user.roles}
    if not roles.intersection({"Super Admin", "Management"}): q = q.filter(Opportunity.owner_id == user.id)
    if stage: q = q.filter(Opportunity.stage == stage)
    if owner_id and roles.intersection({"Super Admin", "Management"}): q = q.filter(Opportunity.owner_id == owner_id)
    return q.order_by(Opportunity.updated_at.desc()).limit(200).all()

@router.patch("/opportunities/{opportunity_id}")
def update_opportunity(opportunity_id: int, data: OpportunityUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    obj = db.get(Opportunity, opportunity_id)
    if not obj: raise HTTPException(404, "Opportunity not found")
    roles = {r.name for r in user.roles}
    if obj.owner_id != user.id and not roles.intersection({"Super Admin", "Management"}): raise HTTPException(403, "Not permitted to update this opportunity")
    changes = data.model_dump(exclude_unset=True)
    if "owner_id" in changes and not roles.intersection({"Super Admin", "Management"}):
        raise HTTPException(403, "Only managers can reassign opportunities")
    if changes.get("stage") == "lost" and not changes.get("lost_reason") and not obj.lost_reason: raise HTTPException(422, "lost_reason is required when marking an opportunity lost")
    if changes.get("lead_id") and not db.get(Lead, changes["lead_id"]): raise HTTPException(404, "Lead not found")
    if changes.get("organization_id") and not db.get(Organization, changes["organization_id"]): raise HTTPException(404, "Organization not found")
    if changes.get("contact_id") and not db.get(Contact, changes["contact_id"]): raise HTTPException(404, "Contact not found")
    old_stage = obj.stage
    for k,v in changes.items(): setattr(obj,k,v)
    if obj.stage != old_stage:
        db.add(PipelineHistory(opportunity_id=obj.id, from_stage=old_stage, to_stage=obj.stage, changed_by_id=user.id, note=changes.get("lost_reason")))
    audit(db,user,"opportunity.updated","opportunity",obj.id,",".join(changes.keys())); db.commit(); db.refresh(obj); return obj

@router.get("/opportunities/{opportunity_id}/history")
def opportunity_history(opportunity_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Opportunity, opportunity_id)
    if not obj: raise HTTPException(404, "Opportunity not found")
    roles = {r.name for r in user.roles}
    if obj.owner_id != user.id and not roles.intersection({"Super Admin", "Management"}): raise HTTPException(403, "Not permitted to view this opportunity")
    return db.query(PipelineHistory).filter_by(opportunity_id=obj.id).order_by(PipelineHistory.changed_at.desc()).all()

@router.post("/opportunities/{opportunity_id}/convert")
def convert_won_opportunity(opportunity_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    obj = db.get(Opportunity, opportunity_id)
    if not obj: raise HTTPException(404, "Opportunity not found")
    roles = {r.name for r in user.roles}
    if obj.owner_id != user.id and not roles.intersection({"Super Admin", "Management"}): raise HTTPException(403, "Not permitted to convert this opportunity")
    if obj.stage != "won": raise HTTPException(422, "Only a won opportunity can be converted to a client")
    lead = db.get(Lead, obj.lead_id) if obj.lead_id else None
    organization = db.get(Organization, obj.organization_id) if obj.organization_id else None
    if not organization:
        organization_name = (lead.organization_name if lead and lead.organization_name else obj.name).strip()
        organization = db.query(Organization).filter(Organization.name.ilike(organization_name)).first()
        if not organization:
            organization = Organization(name=organization_name, organization_type="client")
            db.add(organization); db.flush()
        obj.organization_id = organization.id
    contact = db.get(Contact, obj.contact_id) if obj.contact_id else None
    if not contact and lead:
        contact = db.get(Contact, lead.converted_contact_id) if lead.converted_contact_id else None
        if not contact and lead.email:
            contact = db.query(Contact).filter(Contact.email.ilike(lead.email)).first()
        if not contact:
            contact = Contact(organization_id=organization.id, first_name=lead.first_name, last_name=lead.last_name, email=lead.email, phone=lead.phone)
            db.add(contact); db.flush()
        obj.contact_id = contact.id
        lead.converted_contact_id = contact.id; lead.status = "converted"
    audit(db, user, "opportunity.converted", "opportunity", obj.id, f"organization_id={organization.id}; contact_id={contact.id if contact else ''}")
    db.commit()
    return {"opportunity_id": obj.id, "organization_id": organization.id, "contact_id": contact.id if contact else obj.contact_id, "status": "converted"}

@router.post("/activities", status_code=201)
def create_activity(data: ActivityCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*SALES))):
    if not any([data.lead_id, data.opportunity_id, data.contact_id]): raise HTTPException(422, "Link an activity to a lead, opportunity, or contact")
    values = data.model_dump(); values["owner_id"] = user.id
    obj = Activity(**values); db.add(obj); db.flush(); audit(db,user,"activity.created","activity",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/activities")
def list_activities(lead_id: int | None = None, opportunity_id: int | None = None, contact_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Activity)
    if lead_id: q = q.filter(Activity.lead_id == lead_id)
    if opportunity_id: q = q.filter(Activity.opportunity_id == opportunity_id)
    if contact_id: q = q.filter(Activity.contact_id == contact_id)
    return q.order_by(Activity.occurred_at.desc()).limit(200).all()

@router.post("/tasks", status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*TASK_ROLES))):
    values = data.model_dump(); values["created_by_id"] = user.id
    if values.get("assignee_id") is None: values["assignee_id"] = user.id
    assignee = db.get(User, values["assignee_id"])
    if not assignee: raise HTTPException(404, "Assignee not found")
    if values.get("lead_id") and not db.get(Lead, values["lead_id"]): raise HTTPException(404, "Lead not found")
    if values.get("opportunity_id") and not db.get(Opportunity, values["opportunity_id"]): raise HTTPException(404, "Opportunity not found")
    obj = Task(**values); db.add(obj); db.flush()
    if assignee.id != user.id:
        db.add(Notification(user_id=assignee.id, title="New task assigned", message=f"You were assigned: {obj.title}", related_type="task", related_id=obj.id))
    audit(db,user,"task.created","task",obj.id); db.commit(); db.refresh(obj); return obj

@router.get("/tasks")
def list_tasks(status: str | None = None, overdue_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Task); roles = {r.name for r in user.roles}
    if not roles.intersection({"Super Admin", "Management", "Project / Team Manager"}): q = q.filter(or_(Task.assignee_id == user.id, Task.created_by_id == user.id))
    if status: q = q.filter(Task.status == status)
    if overdue_only: q = q.filter(Task.due_at < datetime.utcnow(), Task.status.notin_(["done", "cancelled"]))
    return q.order_by(Task.due_at.asc().nullslast()).limit(200).all()

@router.patch("/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Task, task_id)
    if not obj: raise HTTPException(404, "Task not found")
    roles = {r.name for r in user.roles}
    if user.id not in (obj.assignee_id, obj.created_by_id) and not roles.intersection({"Super Admin", "Management", "Project / Team Manager"}): raise HTTPException(403, "Not permitted to update this task")
    changes = data.model_dump(exclude_unset=True)
    # Employees can update their own task status/details but cannot reassign tasks.
    if not roles.intersection({"Super Admin", "Management", "Project / Team Manager"}) and "assignee_id" in changes: raise HTTPException(403, "Only managers can reassign tasks")
    if changes.get("assignee_id") is not None and not db.get(User, changes["assignee_id"]): raise HTTPException(404, "Assignee not found")
    old_assignee_id = obj.assignee_id
    new_assignee_id = changes.get("assignee_id")
    for k,v in changes.items(): setattr(obj,k,v)
    if new_assignee_id and new_assignee_id != old_assignee_id and new_assignee_id != user.id:
        db.add(Notification(user_id=new_assignee_id, title="Task assigned to you", message=f"You were assigned: {obj.title}", related_type="task", related_id=obj.id))
    audit(db,user,"task.updated","task",obj.id,",".join(changes.keys())); db.commit(); db.refresh(obj); return obj

@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    roles = {r.name for r in user.roles}; admin = bool(roles.intersection({"Super Admin", "Management"}))
    leads_q = db.query(Lead); opp_q = db.query(Opportunity); tasks_q = db.query(Task)
    if not admin:
        leads_q = leads_q.filter(Lead.owner_id == user.id); opp_q = opp_q.filter(Opportunity.owner_id == user.id)
        tasks_q = tasks_q.filter(or_(Task.assignee_id == user.id, Task.created_by_id == user.id))
    pipeline = opp_q.filter(Opportunity.stage.notin_(["won", "lost"])).with_entities(func.coalesce(func.sum(Opportunity.expected_value), 0)).scalar()
    internship_visible = bool(roles.intersection({"Super Admin", "Management", "Internship Coordinator"}))
    training_visible = bool(roles.intersection({"Super Admin", "Management", "Training Coordinator"}))
    partner_visible = bool(roles.intersection({"Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"}))
    project_visible = bool(roles.intersection({"Super Admin", "Management", "Project / Team Manager"}))
    finance_visible = bool(roles.intersection({"Super Admin", "Management", "Finance / Accounts"}))
    applications = db.query(InternshipApplication)
    if not admin: applications = applications.filter(InternshipApplication.coordinator_id == user.id)
    enrollments = db.query(Enrollment)
    batches = db.query(TrainingBatch)
    partners = db.query(Partner)
    projects = db.query(Project)
    milestones = db.query(ProjectMilestone).join(Project, ProjectMilestone.project_id == Project.id)
    if not admin:
        projects = projects.filter(Project.project_manager_id == user.id)
        milestones = milestones.filter(Project.project_manager_id == user.id)
    total_invoices = db.query(func.coalesce(func.sum(Invoice.amount), 0)).scalar()
    total_payments = db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(PaymentTransaction.status == "received").scalar()
    total_refunds = db.query(func.coalesce(func.sum(Refund.amount), 0)).filter(Refund.status == "processed").scalar()
    net_received = max(Decimal(total_payments) - Decimal(total_refunds), Decimal("0"))
    outstanding = max(Decimal(total_invoices) - net_received, Decimal("0"))
    return {
      "leads_total": leads_q.count(),
      "active_leads": leads_q.filter(Lead.status.notin_(["converted", "lost"])).count(),
      "leads_due_for_follow_up": leads_q.filter(Lead.next_follow_up_at <= datetime.utcnow(), Lead.status.notin_(["converted", "lost"])).count(),
      "opportunities_open": opp_q.filter(Opportunity.stage.notin_(["won", "lost"])).count(),
      "open_pipeline_value": str(pipeline),
      "tasks_open": tasks_q.filter(Task.status.notin_(["done", "cancelled"])).count(),
      "tasks_overdue": tasks_q.filter(Task.due_at < datetime.utcnow(), Task.status.notin_(["done", "cancelled"])).count(),
      "applications_active": applications.filter(InternshipApplication.status.notin_(["completed", "rejected", "withdrawn"])).count() if internship_visible else None,
      "applications_completed": applications.filter(InternshipApplication.status == "completed").count() if internship_visible else None,
      "training_enrollments": enrollments.count() if training_visible else None,
      "training_active_batches": batches.filter(TrainingBatch.status == "active").count() if training_visible else None,
      "active_partners": partners.filter(Partner.status == "active").count() if partner_visible else None,
      "projects_active": projects.filter(Project.status == "active").count() if project_visible else None,
      "milestones_overdue": milestones.filter(ProjectMilestone.due_date < datetime.utcnow().date(), ProjectMilestone.status.notin_(["completed"])).count() if project_visible else None,
      "invoiced_amount": str(total_invoices) if finance_visible else None,
      "payments_received": str(net_received) if finance_visible else None,
      "outstanding_amount": str(outstanding) if finance_visible else None,
    }

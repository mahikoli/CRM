from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Invoice, PaymentTransaction, User, AuditLog, Refund, Organization, Opportunity
from ..schemas import InvoiceCreate, PaymentCreate
from ..extended_schemas import RefundCreate, RefundDecision
from ..security import get_current_user, require_roles

router = APIRouter(tags=["Finance"])
FINANCE = ("Super Admin", "Management", "Finance / Accounts")

@router.post("/invoices", status_code=201)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    if db.query(Invoice).filter(Invoice.invoice_number == data.invoice_number).first():
        raise HTTPException(409, "Invoice number already exists")
    if data.organization_id and not db.get(Organization, data.organization_id): raise HTTPException(404, "Organization not found")
    if data.opportunity_id and not db.get(Opportunity, data.opportunity_id): raise HTTPException(404, "Opportunity not found")
    obj = Invoice(**data.model_dump()); db.add(obj); db.flush()
    db.add(AuditLog(user_id=user.id, action="invoice.created", entity_type="invoice", entity_id=str(obj.id)))
    db.commit(); db.refresh(obj); return {**{c.name: getattr(obj,c.name) for c in obj.__table__.columns}, "amount": str(obj.amount)}

@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    rows = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(200).all()
    result = []
    for inv in rows:
        received = db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(PaymentTransaction.invoice_id == inv.id, PaymentTransaction.status == "received").scalar()
        refunded = db.query(func.coalesce(func.sum(Refund.amount), 0)).join(PaymentTransaction, Refund.payment_id == PaymentTransaction.id).filter(PaymentTransaction.invoice_id == inv.id, Refund.status == "processed").scalar()
        net_received = max(Decimal(received) - Decimal(refunded), Decimal("0"))
        result.append({"id": inv.id, "invoice_number": inv.invoice_number, "organization_id": inv.organization_id, "opportunity_id": inv.opportunity_id, "description": inv.description, "amount": str(inv.amount), "received": str(net_received), "outstanding": str(max(Decimal(inv.amount) - net_received, Decimal("0"))), "due_date": inv.due_date, "status": inv.status})
    return result

@router.post("/payments", status_code=201)
def record_payment(data: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    invoice = db.get(Invoice, data.invoice_id)
    if not invoice: raise HTTPException(404, "Invoice not found")
    if invoice.status == "cancelled": raise HTTPException(409, "Payments cannot be recorded against a cancelled invoice")
    received = db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(PaymentTransaction.invoice_id == invoice.id, PaymentTransaction.status == "received").scalar()
    refunded = db.query(func.coalesce(func.sum(Refund.amount), 0)).join(PaymentTransaction, Refund.payment_id == PaymentTransaction.id).filter(PaymentTransaction.invoice_id == invoice.id, Refund.status == "processed").scalar()
    received = max(Decimal(received) - Decimal(refunded), Decimal("0"))
    if Decimal(received) + data.amount > Decimal(invoice.amount): raise HTTPException(422, "Payment exceeds the outstanding invoice balance")
    values = data.model_dump()
    if values.get("payment_date") is None: values.pop("payment_date")
    obj = PaymentTransaction(**values, recorded_by_id=user.id); db.add(obj); db.flush()
    total = Decimal(received) + data.amount
    invoice.status = "paid" if total == Decimal(invoice.amount) else "partial"
    db.add(AuditLog(user_id=user.id, action="payment.recorded", entity_type="payment_transaction", entity_id=str(obj.id)))
    db.commit(); db.refresh(obj)
    return {"id": obj.id, "invoice_id": obj.invoice_id, "amount": str(obj.amount), "payment_date": obj.payment_date, "method": obj.method, "reference": obj.reference, "invoice_status": invoice.status}

@router.get("/payments")
def list_payments(invoice_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    q = db.query(PaymentTransaction)
    if invoice_id: q = q.filter(PaymentTransaction.invoice_id == invoice_id)
    return [{"id": p.id, "invoice_id": p.invoice_id, "amount": str(p.amount), "payment_date": p.payment_date, "method": p.method, "reference": p.reference, "status": p.status} for p in q.order_by(PaymentTransaction.payment_date.desc()).limit(200).all()]


@router.get("/refunds")
def list_refunds(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    query = db.query(Refund)
    if status: query = query.filter(Refund.status == status)
    return query.order_by(Refund.created_at.desc()).limit(500).all()


@router.post("/refunds", status_code=201)
def request_refund(data: RefundCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    payment = db.get(PaymentTransaction, data.payment_id)
    if not payment or payment.status != "received": raise HTTPException(404, "Received payment not found")
    already_requested = db.query(func.coalesce(func.sum(Refund.amount), 0)).filter(Refund.payment_id == payment.id, Refund.status != "rejected").scalar()
    if Decimal(already_requested) + data.amount > Decimal(payment.amount): raise HTTPException(422, "Total requested refunds cannot exceed the payment amount")
    record = Refund(**data.model_dump(), requested_by_id=user.id, status="requested")
    db.add(record); db.flush()
    db.add(AuditLog(user_id=user.id, action="refund.requested", entity_type="refund", entity_id=str(record.id)))
    db.commit(); db.refresh(record)
    return record


def decide_refund(refund_id: int, data: RefundDecision, db: Session, user: User, next_status: str):
    record = db.get(Refund, refund_id)
    if not record: raise HTTPException(404, "Refund not found")
    if record.status != "requested": raise HTTPException(409, "Only requested refunds can be approved or rejected")
    record.status = next_status
    record.approved_by_id = user.id
    if data.reason: record.reason = f"{record.reason or ''}\nDecision: {data.reason}".strip()
    db.add(AuditLog(user_id=user.id, action=f"refund.{next_status}", entity_type="refund", entity_id=str(record.id)))
    db.commit(); db.refresh(record)
    return record


@router.patch("/refunds/{refund_id}/approve")
def approve_refund(refund_id: int, data: RefundDecision, db: Session = Depends(get_db), user: User = Depends(require_roles("Super Admin", "Management"))):
    return decide_refund(refund_id, data, db, user, "approved")


@router.patch("/refunds/{refund_id}/reject")
def reject_refund(refund_id: int, data: RefundDecision, db: Session = Depends(get_db), user: User = Depends(require_roles("Super Admin", "Management"))):
    return decide_refund(refund_id, data, db, user, "rejected")


@router.patch("/refunds/{refund_id}/process")
def process_refund(refund_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*FINANCE))):
    record = db.get(Refund, refund_id)
    if not record: raise HTTPException(404, "Refund not found")
    if record.status != "approved": raise HTTPException(409, "Only an approved refund can be marked processed")
    payment = db.get(PaymentTransaction, record.payment_id)
    total_processed = db.query(func.coalesce(func.sum(Refund.amount), 0)).filter(Refund.payment_id == payment.id, Refund.status == "processed").scalar()
    if Decimal(total_processed) + record.amount > Decimal(payment.amount): raise HTTPException(422, "Processed refunds cannot exceed the payment amount")
    record.status = "processed"; record.processed_at = datetime.utcnow()
    invoice = db.get(Invoice, payment.invoice_id)
    received = db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0)).filter(PaymentTransaction.invoice_id == invoice.id, PaymentTransaction.status == "received").scalar()
    refunded = db.query(func.coalesce(func.sum(Refund.amount), 0)).join(PaymentTransaction, Refund.payment_id == PaymentTransaction.id).filter(PaymentTransaction.invoice_id == invoice.id, Refund.status == "processed").scalar()
    net_received = max(Decimal(received) - Decimal(refunded), Decimal("0"))
    invoice.status = "unpaid" if net_received == 0 else "paid" if net_received >= Decimal(invoice.amount) else "partial"
    db.add(AuditLog(user_id=user.id, action="refund.processed", entity_type="refund", entity_id=str(record.id)))
    db.commit(); db.refresh(record)
    return {"id": record.id, "payment_id": record.payment_id, "amount": str(record.amount), "status": record.status, "invoice_status": invoice.status}

-- HRUTA OneCRM expanded proposal PostgreSQL schema (reference implementation).
-- This UUID-based schema is separate from the starter API's integer-ID SQLAlchemy
-- models in app/models.py. Do not run it in the database used by the starter API.
-- It creates tables only; it does not create application users or insert business data.

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  phone VARCHAR(30),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(60) NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_roles (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(200) NOT NULL,
  organization_type VARCHAR(30) NOT NULL DEFAULT 'client'
    CHECK (organization_type IN ('client','college','partner','vendor','other')),
  website VARCHAR(500), industry VARCHAR(120), address TEXT, city VARCHAR(100), state VARCHAR(100),
  country VARCHAR(100) DEFAULT 'India', notes TEXT,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  first_name VARCHAR(100) NOT NULL, last_name VARCHAR(100),
  email VARCHAR(255), phone VARCHAR(30), job_title VARCHAR(120),
  notes TEXT, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_email_lower ON contacts (LOWER(email)) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name VARCHAR(100) NOT NULL, last_name VARCHAR(100), email VARCHAR(255), phone VARCHAR(30),
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  company_name VARCHAR(200), source VARCHAR(80) NOT NULL DEFAULT 'manual',
  interest_category VARCHAR(80) NOT NULL DEFAULT 'other'
    CHECK (interest_category IN ('it_services','internship','bootcamp','lms','corporate_training','college_partnership','other')),
  status VARCHAR(30) NOT NULL DEFAULT 'new'
    CHECK (status IN ('new','contacted','qualified','nurturing','converted','lost')),
  priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  next_follow_up_at TIMESTAMPTZ, notes TEXT, lost_reason TEXT,
  converted_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_owner_followup ON leads(owner_id, next_follow_up_at);
CREATE INDEX IF NOT EXISTS idx_leads_email_lower ON leads(LOWER(email)) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS opportunities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(200) NOT NULL,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  primary_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  service_line VARCHAR(80) NOT NULL DEFAULT 'other',
  stage VARCHAR(30) NOT NULL DEFAULT 'qualification'
    CHECK (stage IN ('qualification','discovery','proposal','negotiation','won','lost')),
  expected_value NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (expected_value >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'INR', expected_close_date DATE,
  proposal_status VARCHAR(30) NOT NULL DEFAULT 'not_started'
    CHECK (proposal_status IN ('not_started','draft','sent','accepted','rejected')),
  lost_reason TEXT, description TEXT,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opportunities_owner ON opportunities(owner_id);
CREATE TABLE IF NOT EXISTS pipeline_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  from_stage VARCHAR(30), to_stage VARCHAR(30) NOT NULL,
  changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), note TEXT
);

CREATE TABLE IF NOT EXISTS activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_type VARCHAR(30) NOT NULL CHECK (activity_type IN ('call','email','meeting','note','other')),
  subject VARCHAR(200) NOT NULL, description TEXT, outcome TEXT,
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activities_lead_date ON activities(lead_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(200) NOT NULL, description TEXT,
  status VARCHAR(25) NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','blocked','completed','cancelled')),
  priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
  assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  opportunity_id UUID REFERENCES opportunities(id) ON DELETE SET NULL,
  due_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_due ON tasks(assigned_to, due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, description TEXT,
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  project_manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
  status VARCHAR(25) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','on_hold','completed','cancelled')),
  start_date DATE, target_end_date DATE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS milestones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, description TEXT, due_date DATE,
  status VARCHAR(25) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','completed','delayed')),
  completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS project_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  author_id UUID REFERENCES users(id) ON DELETE SET NULL, update_text TEXT NOT NULL,
  progress_percent SMALLINT CHECK (progress_percent BETWEEN 0 AND 100), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS internship_programs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, domain VARCHAR(120),
  description TEXT, duration_weeks INTEGER CHECK (duration_weeks > 0), mode VARCHAR(20) CHECK (mode IN ('online','onsite','hybrid')),
  fee NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (fee >= 0), is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), program_id UUID REFERENCES internship_programs(id) ON DELETE SET NULL,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  full_name VARCHAR(200) NOT NULL, email VARCHAR(255) NOT NULL, phone VARCHAR(30), college_name VARCHAR(200),
  status VARCHAR(30) NOT NULL DEFAULT 'applied'
    CHECK (status IN ('applied','interview_scheduled','selected','offered','onboarding','active','completed','rejected','withdrawn')),
  coordinator_id UUID REFERENCES users(id) ON DELETE SET NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), start_date DATE, end_date DATE, notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE TABLE IF NOT EXISTS interviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  interviewer_id UUID REFERENCES users(id) ON DELETE SET NULL, scheduled_at TIMESTAMPTZ NOT NULL,
  status VARCHAR(25) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','completed','cancelled','no_show')),
  feedback TEXT, rating SMALLINT CHECK (rating BETWEEN 1 AND 5), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  attendance_date DATE NOT NULL, status VARCHAR(15) NOT NULL CHECK (status IN ('present','absent','leave')),
  recorded_by UUID REFERENCES users(id) ON DELETE SET NULL, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(application_id, attendance_date)
);
CREATE TABLE IF NOT EXISTS internship_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, description TEXT, assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date DATE, status VARCHAR(20) NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned','in_progress','submitted','reviewed','completed')),
  feedback TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  certificate_type VARCHAR(30) NOT NULL CHECK (certificate_type IN ('completion','experience','other')),
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','issued','cancelled')),
  certificate_number VARCHAR(100) UNIQUE, issued_at TIMESTAMPTZ, storage_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(200) NOT NULL, description TEXT,
  syllabus_reference TEXT, price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (price >= 0), is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS trainers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
  name VARCHAR(200) NOT NULL, email VARCHAR(255), phone VARCHAR(30), expertise TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), course_id UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
  trainer_id UUID REFERENCES trainers(id) ON DELETE SET NULL, name VARCHAR(150) NOT NULL,
  start_date DATE, end_date DATE, mode VARCHAR(20) CHECK (mode IN ('online','onsite','hybrid')),
  status VARCHAR(20) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','completed','cancelled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE RESTRICT,
  application_id UUID REFERENCES applications(id) ON DELETE SET NULL,
  student_name VARCHAR(200) NOT NULL, student_email VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'enrolled' CHECK (status IN ('enrolled','in_progress','completed','withdrawn')),
  enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), completed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS training_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ,
  meeting_url TEXT, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS session_attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
  enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
  status VARCHAR(15) NOT NULL CHECK (status IN ('present','absent','late','excused')),
  UNIQUE(session_id, enrollment_id)
);
CREATE TABLE IF NOT EXISTS assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, max_score NUMERIC(8,2) NOT NULL DEFAULT 100 CHECK (max_score > 0), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS assessment_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
  score NUMERIC(8,2) NOT NULL CHECK (score >= 0), feedback TEXT, submitted_at TIMESTAMPTZ,
  UNIQUE(assessment_id, enrollment_id)
);
CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), enrollment_id UUID REFERENCES enrollments(id) ON DELETE CASCADE,
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
  rating SMALLINT CHECK (rating BETWEEN 1 AND 5), comments TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (enrollment_id IS NOT NULL OR application_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  name VARCHAR(200) NOT NULL, partner_type VARCHAR(40) NOT NULL DEFAULT 'college',
  primary_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'prospect' CHECK (status IN ('prospect','active','inactive','expired')),
  notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS partnership_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  activity_type VARCHAR(40) NOT NULL, title VARCHAR(200) NOT NULL, description TEXT,
  activity_date DATE, owner_id UUID REFERENCES users(id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS agreements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, start_date DATE, end_date DATE, status VARCHAR(20) NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','active','renewal_due','expired','terminated')),
  storage_key TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), invoice_number VARCHAR(80) NOT NULL UNIQUE,
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
  opportunity_id UUID REFERENCES opportunities(id) ON DELETE SET NULL,
  enrollment_id UUID REFERENCES enrollments(id) ON DELETE SET NULL,
  issue_date DATE NOT NULL DEFAULT CURRENT_DATE, due_date DATE,
  currency CHAR(3) NOT NULL DEFAULT 'INR', total_amount NUMERIC(14,2) NOT NULL CHECK (total_amount >= 0),
  status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','issued','partially_paid','paid','overdue','cancelled')),
  notes TEXT, created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS payment_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0), currency CHAR(3) NOT NULL DEFAULT 'INR',
  payment_method VARCHAR(30) CHECK (payment_method IN ('cash','bank_transfer','upi','card','gateway','other')),
  transaction_reference VARCHAR(200), status VARCHAR(20) NOT NULL DEFAULT 'received'
    CHECK (status IN ('pending','received','failed','reversed')),
  paid_at TIMESTAMPTZ, recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payment_transactions(invoice_id, status);
CREATE TABLE IF NOT EXISTS payment_allocations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), payment_id UUID NOT NULL REFERENCES payment_transactions(id) ON DELETE RESTRICT,
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS refunds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), payment_id UUID NOT NULL REFERENCES payment_transactions(id) ON DELETE RESTRICT,
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0), reason TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','approved','rejected','processed')),
  requested_by UUID REFERENCES users(id) ON DELETE SET NULL, approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
  processed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL, message TEXT NOT NULL, channel VARCHAR(20) NOT NULL DEFAULT 'in_app'
    CHECK (channel IN ('in_app','email')), status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','sent','failed','read')),
  related_type VARCHAR(60), related_id UUID, scheduled_at TIMESTAMPTZ, sent_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action VARCHAR(100) NOT NULL, entity_type VARCHAR(100) NOT NULL, entity_id UUID,
  old_values JSONB, new_values JSONB, ip_address INET, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at DESC);
CREATE TABLE IF NOT EXISTS integration_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), integration_name VARCHAR(100) NOT NULL,
  operation VARCHAR(150) NOT NULL, status VARCHAR(20) NOT NULL CHECK (status IN ('success','failed','retrying')),
  external_reference VARCHAR(255), request_summary JSONB, response_summary JSONB, error_message TEXT,
  attempts INTEGER NOT NULL DEFAULT 1 CHECK (attempts > 0), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS app_configuration (
  key VARCHAR(120) PRIMARY KEY, value JSONB NOT NULL, description TEXT,
  updated_by UUID REFERENCES users(id) ON DELETE SET NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Initial roles. Review and adjust names to HRUTA's approved access policy.
INSERT INTO roles(name, description) VALUES
 ('super_admin','System configuration, users, roles and audit records'),
 ('management','Approved business-wide dashboards and reports'),
 ('sales','Assigned leads, opportunities, contacts and follow-ups'),
 ('internship_coordinator','Internship applications and progress'),
 ('training_coordinator','Courses, batches, enrolments and attendance'),
 ('finance','Invoices, payments and finance reports'),
 ('marketing','Campaign/source information and permitted lead access'),
 ('project_manager','Assigned projects, tasks and milestones'),
 ('employee','Assigned tasks and permitted work updates'),
 ('intern','Assigned tasks and permitted internship records')
ON CONFLICT (name) DO NOTHING;

COMMIT;

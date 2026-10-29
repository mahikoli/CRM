import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BriefcaseBusiness,
  Building2, CalendarDays, Check, ChevronDown, CircleDollarSign, Clock3,
  ContactRound, FileText, GraduationCap, LayoutDashboard, LogOut, Menu, Plus,
  RefreshCw, Search, Send, ShieldCheck, Sparkles, Target, UserRound,
  UsersRound, X, CheckCircle2, ListTodo, Mail, LockKeyhole, Handshake,
  FolderKanban, ClipboardList, BarChart3, Settings, Download,
  Pencil, Award, UserCog, FileSpreadsheet, CalendarCheck2,
} from "lucide-react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

async function request(path, { token, body, form, multipart, method = "GET" } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (form) headers["Content-Type"] = "application/x-www-form-urlencoded";
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : (multipart || form),
    });
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE}. Start the backend and try again.`);
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.slice(-1)[0] || "Field"}: ${item.msg}`).join(" · ")
      : detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

const PAGE_META = {
  overview: { label: "Overview", title: "Good morning", icon: LayoutDashboard },
  leads: { label: "Leads", title: "Leads", icon: Target, endpoint: "/leads?page=1&page_size=100", key: "leads", action: "lead" },
  organizations: { label: "Organizations", title: "Organizations", icon: Building2, endpoint: "/organizations?page=1&page_size=100", key: "organizations", action: "organization" },
  contacts: { label: "Contacts", title: "Contacts", icon: ContactRound, endpoint: "/contacts?page=1&page_size=100", key: "contacts", action: "contact" },
  opportunities: { label: "Opportunities", title: "Opportunities", icon: BriefcaseBusiness, endpoint: "/opportunities", key: "opportunities", action: "opportunity" },
  proposals: { label: "Proposals", title: "Sales proposals", icon: FileText, endpoint: "/sales/proposals", key: "proposals", action: "proposal" },
  tasks: { label: "Tasks", title: "Tasks", icon: ListTodo, endpoint: "/tasks", key: "tasks", action: "task" },
  activities: { label: "Activities", title: "Activities", icon: Activity, endpoint: "/activities", key: "activities", action: "activity" },
  invoices: { label: "Invoices", title: "Invoices", icon: FileText, endpoint: "/invoices", key: "invoices", action: "invoice" },
  payments: { label: "Payments", title: "Payments", icon: CircleDollarSign, endpoint: "/payments", key: "payments", action: "payment" },
  refunds: { label: "Refunds", title: "Refunds", icon: CircleDollarSign, endpoint: "/refunds", key: "refunds", action: "refund" },
  programs: { label: "Programs", title: "Internship programs", icon: GraduationCap, endpoint: "/internships/programs", key: "programs", action: "program" },
  applications: { label: "Applications", title: "Internship applications", icon: UsersRound, endpoint: "/internships/applications", key: "applications", action: "application" },
  interviews: { label: "Interviews", title: "Interviews", icon: CalendarDays, endpoint: "/internships/interviews", key: "interviews", action: "interview" },
  allocations: { label: "Allocations", title: "Intern allocations", icon: UsersRound, endpoint: "/internships/allocations", key: "allocations", action: "allocation" },
  internAttendance: { label: "Attendance", title: "Intern attendance", icon: CalendarCheck2, endpoint: "/internships/attendance", key: "internAttendance", action: "internAttendance" },
  internTasks: { label: "Intern tasks", title: "Internship tasks", icon: ClipboardList, endpoint: "/internships/tasks", key: "internTasks", action: "internTask" },
  certificates: { label: "Certificates", title: "Certificates & letters", icon: Award, endpoint: "/internships/certificates", key: "certificates", action: "certificate" },
  courses: { label: "Courses", title: "Courses & bootcamps", icon: GraduationCap, endpoint: "/training/courses", key: "courses", action: "course" },
  trainers: { label: "Trainers", title: "Trainers", icon: UserRound, endpoint: "/training/trainers", key: "trainers", action: "trainer" },
  batches: { label: "Batches", title: "Training batches", icon: UsersRound, endpoint: "/training/batches", key: "batches", action: "batch" },
  enrollments: { label: "Enrollments", title: "Enrollments", icon: ContactRound, endpoint: "/training/enrollments", key: "enrollments", action: "enrollment" },
  sessions: { label: "Sessions", title: "Training sessions", icon: CalendarDays, endpoint: "/training/sessions", key: "sessions", action: "session" },
  trainingAttendance: { label: "Attendance", title: "Training attendance", icon: CalendarCheck2, endpoint: "/training/attendance", key: "trainingAttendance", action: "trainingAttendance" },
  assessments: { label: "Assessments", title: "Assessments", icon: ClipboardList, endpoint: "/training/assessments", key: "assessments", action: "assessment" },
  results: { label: "Results", title: "Assessment results", icon: BarChart3, endpoint: "/training/results", key: "results", action: "result" },
  feedback: { label: "Feedback", title: "Learner feedback", icon: CheckCircle2, endpoint: "/training/feedback", key: "feedback", action: "feedback" },
  partners: { label: "Partners", title: "Partnerships", icon: Handshake, endpoint: "/partners", key: "partners", action: "partner" },
  partnershipActivities: { label: "Activities", title: "Partner activities", icon: Activity, endpoint: "/partnership-activities", key: "partnershipActivities", action: "partnershipActivity" },
  agreements: { label: "Agreements", title: "Partnership agreements", icon: FileText, endpoint: "/partnership-agreements", key: "agreements", action: "agreement" },
  projects: { label: "Projects", title: "Client projects", icon: FolderKanban, endpoint: "/projects", key: "projects", action: "project" },
  milestones: { label: "Milestones", title: "Project milestones", icon: Target, endpoint: "/project-milestones", key: "milestones", action: "milestone" },
  projectUpdates: { label: "Progress updates", title: "Project updates", icon: Activity, endpoint: "/project-updates", key: "projectUpdates", action: "projectUpdate" },
  projectTasks: { label: "Project tasks", title: "Project tasks", icon: ListTodo, endpoint: "/project-tasks", key: "projectTasks", action: "projectTask" },
  notifications: { label: "Notifications", title: "Notifications", icon: Bell, endpoint: "/notifications", key: "notifications" },
  documents: { label: "Documents", title: "Documents & evidence", icon: FileText },
  reports: { label: "Reports", title: "Reports & exports", icon: BarChart3 },
  adminUsers: { label: "User access", title: "User access", icon: UserCog },
  configuration: { label: "Settings", title: "Workflow settings", icon: Settings },
  auditLogs: { label: "Audit log", title: "Audit log", icon: ShieldCheck, endpoint: "/admin/audit-logs", key: "auditLogs" },
};

const PAGE_ACCESS = {
  proposals: ["Super Admin", "Management", "Sales / Business Development"],
  invoices: ["Super Admin", "Management", "Finance / Accounts"], payments: ["Super Admin", "Management", "Finance / Accounts"],
  programs: ["Super Admin", "Management", "Internship Coordinator"], applications: ["Super Admin", "Management", "Internship Coordinator"],
  interviews: ["Super Admin", "Management", "Internship Coordinator"], allocations: ["Super Admin", "Management", "Internship Coordinator"], internAttendance: ["Super Admin", "Management", "Internship Coordinator"],
  internTasks: ["Super Admin", "Management", "Internship Coordinator"], certificates: ["Super Admin", "Management", "Internship Coordinator"],
  courses: ["Super Admin", "Management", "Training Coordinator"], trainers: ["Super Admin", "Management", "Training Coordinator"],
  batches: ["Super Admin", "Management", "Training Coordinator"], enrollments: ["Super Admin", "Management", "Training Coordinator"],
  sessions: ["Super Admin", "Management", "Training Coordinator"], trainingAttendance: ["Super Admin", "Management", "Training Coordinator"],
  assessments: ["Super Admin", "Management", "Training Coordinator"], results: ["Super Admin", "Management", "Training Coordinator"],
  feedback: ["Super Admin", "Management", "Training Coordinator", "Internship Coordinator"],
  partners: ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"],
  partnershipActivities: ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"],
  agreements: ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"],
  documents: ["Super Admin", "Management", "Sales / Business Development", "Finance / Accounts", "Internship Coordinator", "Training Coordinator", "Project / Team Manager", "Employee / Intern"],
  projects: ["Super Admin", "Management", "Project / Team Manager"], milestones: ["Super Admin", "Management", "Project / Team Manager"],
  projectUpdates: ["Super Admin", "Management", "Project / Team Manager"], projectTasks: ["Super Admin", "Management", "Project / Team Manager", "Employee / Intern"],
  refunds: ["Super Admin", "Management", "Finance / Accounts"], auditLogs: ["Super Admin"],
  adminUsers: ["Super Admin"], configuration: ["Super Admin"],
};

const FORM_META = {
  lead: { title: "Add a lead", endpoint: "/leads", fields: [
    { name: "first_name", label: "First name", required: true }, { name: "last_name", label: "Last name" },
    { name: "email", label: "Email", type: "email" }, { name: "phone", label: "Phone" },
    { name: "organization_name", label: "Organization" }, { name: "interest", label: "Interested in", required: true, placeholder: "e.g. IT services, internship" },
    { name: "source", label: "Source", placeholder: "manual" },
    { name: "priority", label: "Priority", type: "select", default: "medium", options: ["low", "medium", "high"] },
    { name: "next_follow_up_at", label: "Next follow-up", type: "datetime-local" },
    { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  organization: { title: "Add an organization", endpoint: "/organizations", fields: [
    { name: "name", label: "Organization name", required: true },
    { name: "organization_type", label: "Type", type: "select", options: ["client", "college", "partner", "prospect"] },
    { name: "industry", label: "Industry" }, { name: "website", label: "Website", type: "url" },
    { name: "address", label: "Address", type: "textarea", wide: true }, { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  contact: { title: "Add a contact", endpoint: "/contacts", fields: [
    { name: "first_name", label: "First name", required: true }, { name: "last_name", label: "Last name" },
    { name: "email", label: "Email", type: "email" }, { name: "phone", label: "Phone" },
    { name: "organization_id", label: "Organization", relation: "organizations" }, { name: "designation", label: "Designation" },
  ] },
  opportunity: { title: "Create an opportunity", endpoint: "/opportunities", fields: [
    { name: "name", label: "Opportunity name", required: true },
    { name: "stage", label: "Stage", type: "select", default: "qualification", options: ["qualification", "proposal", "negotiation", "won"] },
    { name: "expected_value", label: "Expected value", type: "number", placeholder: "0.00" },
    { name: "expected_close_date", label: "Expected close date", type: "date" },
    { name: "lead_id", label: "Related lead", relation: "leads" }, { name: "organization_id", label: "Organization", relation: "organizations" },
    { name: "contact_id", label: "Primary contact", relation: "contacts" },
  ] },
  task: { title: "Create a task", endpoint: "/tasks", fields: [
    { name: "title", label: "Task title", required: true },
    { name: "priority", label: "Priority", type: "select", default: "medium", options: ["low", "medium", "high"] },
    { name: "status", label: "Status", type: "select", default: "todo", options: ["todo", "in_progress", "blocked", "done", "cancelled"] },
    { name: "due_at", label: "Due date and time", type: "datetime-local" },
    { name: "assignee_id", label: "Assign to", relation: "users" },
    { name: "lead_id", label: "Related lead", relation: "leads" }, { name: "opportunity_id", label: "Related opportunity", relation: "opportunities" },
    { name: "description", label: "Description", type: "textarea", wide: true },
  ] },
  activity: { title: "Log an activity", endpoint: "/activities", fields: [
    { name: "subject", label: "Subject", required: true },
    { name: "activity_type", label: "Type", type: "select", options: ["call", "email", "meeting", "note"] },
    { name: "lead_id", label: "Related lead", relation: "leads" }, { name: "opportunity_id", label: "Related opportunity", relation: "opportunities" },
    { name: "contact_id", label: "Related contact", relation: "contacts" },
    { name: "occurred_at", label: "Date and time", type: "datetime-local" },
    { name: "outcome", label: "Outcome", placeholder: "e.g. Follow-up scheduled" },
    { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  invoice: { title: "Create an invoice", endpoint: "/invoices", fields: [
    { name: "invoice_number", label: "Invoice number", required: true },
    { name: "description", label: "Description", required: true },
    { name: "amount", label: "Amount", type: "number", required: true },
    { name: "due_date", label: "Due date", type: "date" },
    { name: "organization_id", label: "Organization", relation: "organizations" }, { name: "opportunity_id", label: "Opportunity", relation: "opportunities" },
  ] },
  payment: { title: "Record a payment", endpoint: "/payments", fields: [
    { name: "invoice_id", label: "Invoice", relation: "invoices", required: true },
    { name: "amount", label: "Payment amount", type: "number", required: true },
    { name: "payment_date", label: "Payment date", type: "date" },
    { name: "method", label: "Method", required: true, placeholder: "e.g. bank transfer, UPI" },
    { name: "reference", label: "Reference" },
  ] },
  proposal: { title: "Create a proposal", endpoint: "/sales/proposals", fields: [
    { name: "opportunity_id", label: "Opportunity", relation: "opportunities", required: true },
    { name: "title", label: "Proposal title", required: true }, { name: "version", label: "Version", type: "number", default: "1" },
    { name: "amount", label: "Proposed amount", type: "number" },
    { name: "status", label: "Status", type: "select", options: ["draft", "sent", "accepted", "rejected"] },
    { name: "response_notes", label: "Notes", type: "textarea", wide: true },
  ] },
  program: { title: "Add an internship program", endpoint: "/internships/programs", fields: [
    { name: "name", label: "Program name", required: true }, { name: "domain", label: "Domain" },
    { name: "duration_weeks", label: "Duration (weeks)", type: "number" },
    { name: "mode", label: "Mode", type: "select", options: ["online", "onsite", "hybrid"] },
    { name: "fee", label: "Program fee", type: "number" }, { name: "description", label: "Description", type: "textarea", wide: true },
  ] },
  application: { title: "Register an intern", endpoint: "/internships/applications", fields: [
    { name: "full_name", label: "Student name", required: true }, { name: "email", label: "Email", type: "email", required: true },
    { name: "phone", label: "Phone" }, { name: "college_name", label: "College" },
    { name: "program_id", label: "Program", relation: "programs" }, { name: "lead_id", label: "Enquiry lead", relation: "leads" },
    { name: "coordinator_id", label: "Coordinator", relation: "users" }, { name: "status", label: "Status", type: "select", options: ["applied", "interview_scheduled", "selected", "offered", "onboarding", "active", "completed", "rejected", "withdrawn"] },
    { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" },
    { name: "team_name", label: "Team" }, { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  interview: { title: "Schedule an interview", endpoint: "/internships/interviews", fields: [
    { name: "application_id", label: "Application", relation: "applications", required: true },
    { name: "interviewer_id", label: "Interviewer", relation: "users" }, { name: "scheduled_at", label: "Date and time", type: "datetime-local", required: true },
    { name: "status", label: "Status", type: "select", options: ["scheduled", "completed", "cancelled", "no_show"] },
    { name: "rating", label: "Rating (1–5)", type: "number" }, { name: "feedback", label: "Feedback", type: "textarea", wide: true },
  ] },
  allocation: { title: "Allocate an intern", endpoint: "/internships/allocations", fields: [
    { name: "application_id", label: "Intern", relation: "applications", required: true }, { name: "team_name", label: "Team", required: true },
    { name: "coordinator_id", label: "Coordinator", relation: "users" }, { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  internAttendance: { title: "Record intern attendance", endpoint: "/internships/attendance", fields: [
    { name: "application_id", label: "Intern", relation: "applications", required: true }, { name: "attendance_date", label: "Date", type: "date", required: true },
    { name: "status", label: "Status", type: "select", options: ["present", "absent", "leave"] }, { name: "notes", label: "Notes" },
  ] },
  internTask: { title: "Assign an internship task", endpoint: "/internships/tasks", fields: [
    { name: "application_id", label: "Intern", relation: "applications", required: true }, { name: "title", label: "Task", required: true },
    { name: "due_date", label: "Due date", type: "date" }, { name: "description", label: "Description", type: "textarea", wide: true },
  ] },
  certificate: { title: "Prepare a certificate or letter", endpoint: "/internships/certificates", fields: [
    { name: "application_id", label: "Intern", relation: "applications", required: true },
    { name: "certificate_type", label: "Document type", type: "select", options: ["completion", "experience", "other"] },
    { name: "certificate_number", label: "Certificate number" },
  ] },
  course: { title: "Add a course", endpoint: "/training/courses", fields: [
    { name: "name", label: "Course name", required: true }, { name: "price", label: "Price", type: "number" },
    { name: "syllabus_reference", label: "Syllabus reference" }, { name: "description", label: "Description", type: "textarea", wide: true },
  ] },
  trainer: { title: "Add a trainer", endpoint: "/training/trainers", fields: [
    { name: "name", label: "Trainer name", required: true }, { name: "user_id", label: "Linked user", relation: "users" },
    { name: "email", label: "Email", type: "email" }, { name: "phone", label: "Phone" }, { name: "expertise", label: "Expertise", type: "textarea", wide: true },
  ] },
  batch: { title: "Create a batch", endpoint: "/training/batches", fields: [
    { name: "course_id", label: "Course", relation: "courses", required: true }, { name: "trainer_id", label: "Trainer", relation: "trainers" },
    { name: "name", label: "Batch name", required: true }, { name: "mode", label: "Mode", type: "select", options: ["online", "onsite", "hybrid"] },
    { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" },
  ] },
  enrollment: { title: "Enroll a learner", endpoint: "/training/enrollments", fields: [
    { name: "batch_id", label: "Batch", relation: "batches", required: true }, { name: "application_id", label: "Internship application", relation: "applications" },
    { name: "student_name", label: "Learner name", required: true }, { name: "student_email", label: "Learner email", type: "email", required: true },
  ] },
  session: { title: "Schedule a session", endpoint: "/training/sessions", fields: [
    { name: "batch_id", label: "Batch", relation: "batches", required: true }, { name: "title", label: "Session title", required: true },
    { name: "starts_at", label: "Starts at", type: "datetime-local", required: true }, { name: "ends_at", label: "Ends at", type: "datetime-local" },
    { name: "meeting_url", label: "Meeting link", type: "url" }, { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  trainingAttendance: { title: "Record class attendance", endpoint: "/training/attendance", fields: [
    { name: "session_id", label: "Session", relation: "sessions", required: true }, { name: "enrollment_id", label: "Learner", relation: "enrollments", required: true },
    { name: "status", label: "Attendance", type: "select", options: ["present", "absent", "late", "excused"] },
  ] },
  assessment: { title: "Create an assessment", endpoint: "/training/assessments", fields: [
    { name: "course_id", label: "Course", relation: "courses" }, { name: "title", label: "Assessment title", required: true },
    { name: "max_score", label: "Maximum score", type: "number", default: "100" },
  ] },
  result: { title: "Record an assessment result", endpoint: "/training/results", fields: [
    { name: "assessment_id", label: "Assessment", relation: "assessments", required: true }, { name: "enrollment_id", label: "Learner", relation: "enrollments", required: true },
    { name: "score", label: "Score", type: "number", required: true }, { name: "submitted_at", label: "Submitted at", type: "datetime-local" },
    { name: "feedback", label: "Feedback", type: "textarea", wide: true },
  ] },
  feedback: { title: "Record learner feedback", endpoint: "/training/feedback", fields: [
    { name: "enrollment_id", label: "Training enrollment", relation: "enrollments" }, { name: "application_id", label: "Internship application", relation: "applications" },
    { name: "rating", label: "Rating (1–5)", type: "number" }, { name: "comments", label: "Comments", type: "textarea", wide: true },
  ] },
  partner: { title: "Add a partner", endpoint: "/partners", fields: [
    { name: "name", label: "Partner name", required: true }, { name: "partner_type", label: "Partner type", placeholder: "college, company, vendor" },
    { name: "organization_id", label: "Organization", relation: "organizations" }, { name: "primary_contact_id", label: "Primary contact", relation: "contacts" },
    { name: "status", label: "Status", type: "select", options: ["prospect", "active", "inactive", "expired"] }, { name: "notes", label: "Notes", type: "textarea", wide: true },
  ] },
  partnershipActivity: { title: "Log a partner activity", endpoint: "/partnership-activities", fields: [
    { name: "partner_id", label: "Partner", relation: "partners", required: true }, { name: "activity_type", label: "Type", required: true },
    { name: "title", label: "Activity title", required: true }, { name: "activity_date", label: "Date", type: "date" },
    { name: "description", label: "Details", type: "textarea", wide: true },
  ] },
  agreement: { title: "Add an agreement", endpoint: "/partnership-agreements", fields: [
    { name: "partner_id", label: "Partner", relation: "partners", required: true }, { name: "title", label: "Agreement title", required: true },
    { name: "status", label: "Status", type: "select", options: ["draft", "active", "renewal_due", "expired", "terminated"] },
    { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "Renewal / end date", type: "date" },
  ] },
  project: { title: "Create a project", endpoint: "/projects", fields: [
    { name: "name", label: "Project name", required: true }, { name: "organization_id", label: "Client organization", relation: "organizations" },
    { name: "project_manager_id", label: "Project manager", relation: "users" },
    { name: "status", label: "Status", type: "select", options: ["planned", "active", "on_hold", "completed", "cancelled"] },
    { name: "start_date", label: "Start date", type: "date" }, { name: "target_end_date", label: "Target end date", type: "date" },
    { name: "description", label: "Project description", type: "textarea", wide: true },
  ] },
  milestone: { title: "Add a milestone", endpoint: "/project-milestones", fields: [
    { name: "project_id", label: "Project", relation: "projects", required: true }, { name: "title", label: "Milestone", required: true },
    { name: "due_date", label: "Due date", type: "date" }, { name: "status", label: "Status", type: "select", options: ["pending", "in_progress", "completed", "delayed"] },
    { name: "description", label: "Details", type: "textarea", wide: true },
  ] },
  projectUpdate: { title: "Post a project update", endpoint: "/project-updates", fields: [
    { name: "project_id", label: "Project", relation: "projects", required: true }, { name: "progress_percent", label: "Progress (%)", type: "number" },
    { name: "update_text", label: "Update", type: "textarea", required: true, wide: true },
  ] },
  projectTask: { title: "Create a project task", endpoint: "/project-tasks", fields: [
    { name: "project_id", label: "Project", relation: "projects", required: true }, { name: "title", label: "Task", required: true },
    { name: "assignee_id", label: "Assign to", relation: "users" }, { name: "due_at", label: "Due date", type: "datetime-local" },
    { name: "priority", label: "Priority", type: "select", options: ["low", "medium", "high"] }, { name: "description", label: "Description", type: "textarea", wide: true },
  ] },
  refund: { title: "Request a refund", endpoint: "/refunds", fields: [
    { name: "payment_id", label: "Payment", relation: "payments", required: true }, { name: "amount", label: "Refund amount", type: "number", required: true },
    { name: "reason", label: "Reason", type: "textarea", required: true, wide: true },
  ] },
};

const NAV_GROUPS = [
  { label: "CRM & SALES", items: ["overview", "leads", "organizations", "contacts", "opportunities", "proposals"] },
  { label: "INTERNSHIPS", items: ["programs", "applications", "interviews", "allocations", "internAttendance", "internTasks", "certificates"] },
  { label: "TRAINING & LMS", items: ["courses", "trainers", "batches", "enrollments", "sessions", "trainingAttendance", "assessments", "results", "feedback"] },
  { label: "PARTNERSHIPS", items: ["partners", "partnershipActivities", "agreements"] },
  { label: "PROJECT DELIVERY", items: ["projects", "milestones", "projectUpdates", "projectTasks"] },
  { label: "FINANCE", items: ["invoices", "payments", "refunds"] },
  { label: "INSIGHTS & ADMIN", items: ["notifications", "documents", "reports", "adminUsers", "auditLogs", "configuration"] },
];

const EMPTY_DATA = {
  summary: null, reportSummary: null, leads: [], organizations: [], contacts: [], opportunities: [], proposals: [],
  tasks: [], activities: [], invoices: [], payments: [], refunds: [], programs: [], applications: [], interviews: [], allocations: [],
  internAttendance: [], internTasks: [], certificates: [], courses: [], trainers: [], batches: [], enrollments: [],
  sessions: [], trainingAttendance: [], assessments: [], results: [], feedback: [], partners: [], partnershipActivities: [],
  agreements: [], projects: [], milestones: [], projectUpdates: [], projectTasks: [], notifications: [], roles: [],
  directoryUsers: [], adminUsersData: [], auditLogs: [], configuration: [],
};

const formatMoney = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "U";
const niceDate = (value) => value ? new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value)) : "—";
const displayName = (row) => [row.first_name, row.last_name].filter(Boolean).join(" ") || row.full_name || "—";
const statusTone = (value = "") => ({ new: "blue", planned: "blue", scheduled: "blue", enrolled: "blue", qualified: "green", won: "green", paid: "green", done: "green", active: "green", completed: "green", selected: "green", issued: "green", approved: "green", processed: "green", present: "green", contacted: "violet", proposal: "violet", partial: "amber", in_progress: "amber", renewal_due: "amber", medium: "amber", lost: "red", overdue: "red", blocked: "red", high: "red", rejected: "red", cancelled: "red", expired: "red", absent: "red", delayed: "red", low: "slate", todo: "slate", unpaid: "amber" }[value.toLowerCase()] || "slate");

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("onecrm_token") || "");
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(localStorage.getItem("onecrm_token")));
  const [page, setPage] = useState("overview");
  const [data, setData] = useState(EMPTY_DATA);
  const [dataBusy, setDataBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState("");
  const [managedUser, setManagedUser] = useState(null);
  const [toast, setToast] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const roles = user?.roles || [];
  const canSell = roles.some((role) => ["Super Admin", "Management", "Sales / Business Development"].includes(role));
  const hasRole = (...allowed) => roles.some((role) => allowed.includes(role));
  const canAccessPage = (key) => !PAGE_ACCESS[key] || hasRole(...PAGE_ACCESS[key]);
  const canCreatePage = (key) => {
    if (key === "tasks") return hasRole("Super Admin", "Management", "Sales / Business Development", "Internship Coordinator", "Training Coordinator", "Project / Team Manager", "Employee / Intern");
    if (key === "projectTasks") return hasRole("Super Admin", "Management", "Project / Team Manager");
    if (["notifications", "reports", "adminUsers", "auditLogs", "configuration"].includes(key)) return false;
    return PAGE_META[key]?.action ? (PAGE_ACCESS[key] ? canAccessPage(key) : canSell) : false;
  };

  const loadWorkspace = useCallback(async (activeToken, currentUser) => {
    setDataBusy(true);
    const roleSet = new Set(currentUser.roles || []);
    const hasAny = (...items) => items.some((role) => roleSet.has(role));
    const requests = [
      ["summary", "/dashboard/summary"], ["leads", "/leads?page=1&page_size=100"],
      ["organizations", "/organizations?page=1&page_size=100"], ["contacts", "/contacts?page=1&page_size=100"],
      ["opportunities", "/opportunities"], ["tasks", "/tasks"], ["activities", "/activities"],
      ["notifications", "/notifications"], ["reportSummary", "/reports/summary"], ["directoryUsers", "/directory/users"],
    ];
    if (hasAny("Super Admin", "Management", "Sales / Business Development")) requests.push(["proposals", "/sales/proposals"]);
    if (hasAny("Super Admin", "Management", "Finance / Accounts")) {
      requests.push(["invoices", "/invoices"], ["payments", "/payments"], ["refunds", "/refunds"]);
    }
    if (hasAny("Super Admin", "Management", "Internship Coordinator")) requests.push(
      ["programs", "/internships/programs"], ["applications", "/internships/applications"], ["interviews", "/internships/interviews"],
      ["allocations", "/internships/allocations"],
      ["internAttendance", "/internships/attendance"], ["internTasks", "/internships/tasks"], ["certificates", "/internships/certificates"],
    );
    if (hasAny("Super Admin", "Management", "Training Coordinator")) requests.push(
      ["courses", "/training/courses"], ["trainers", "/training/trainers"], ["batches", "/training/batches"],
      ["enrollments", "/training/enrollments"], ["sessions", "/training/sessions"], ["trainingAttendance", "/training/attendance"],
      ["assessments", "/training/assessments"], ["results", "/training/results"], ["feedback", "/training/feedback"],
    );
    else if (hasAny("Internship Coordinator")) requests.push(["feedback", "/training/feedback"]);
    if (hasAny("Super Admin", "Management", "Sales / Business Development", "Internship Coordinator")) requests.push(
      ["partners", "/partners"], ["partnershipActivities", "/partnership-activities"], ["agreements", "/partnership-agreements"],
    );
    if (hasAny("Super Admin", "Management", "Project / Team Manager")) requests.push(
      ["projects", "/projects"], ["milestones", "/project-milestones"], ["projectUpdates", "/project-updates"], ["projectTasks", "/project-tasks"],
    );
    else if (hasAny("Employee / Intern")) requests.push(["projectTasks", "/project-tasks"]);
    if (roleSet.has("Super Admin")) requests.push(
      ["adminUsersData", "/admin/users"], ["roles", "/admin/roles"], ["auditLogs", "/admin/audit-logs?page=1&page_size=100"], ["configuration", "/admin/configuration"],
    );
    const results = await Promise.all(requests.map(async ([key, path]) => {
      try { return [key, await request(path, { token: activeToken })]; }
      catch { return [key, key === "summary" ? null : []]; }
    }));
    setData({ ...EMPTY_DATA, ...Object.fromEntries(results) });
    setDataBusy(false);
  }, []);

  useEffect(() => {
    if (!token) { setBooting(false); setUser(null); return; }
    let alive = true;
    request("/auth/me", { token }).then((me) => {
      if (alive) setUser(me);
    }).catch(() => {
      localStorage.removeItem("onecrm_token");
      if (alive) { setToken(""); setUser(null); }
    }).finally(() => { if (alive) setBooting(false); });
    return () => { alive = false; };
  }, [token]);

  useEffect(() => {
    if (token && user) loadWorkspace(token, user);
  }, [token, user, loadWorkspace]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const logout = () => {
    localStorage.removeItem("onecrm_token");
    setToken(""); setUser(null); setData(EMPTY_DATA); setPage("overview");
  };

  const authenticate = async (email, password) => {
    const form = new URLSearchParams({ username: email, password });
    const result = await request("/auth/login", { method: "POST", form });
    localStorage.setItem("onecrm_token", result.access_token);
    setToken(result.access_token);
  };

  const register = async (values) => request("/auth/register", { method: "POST", body: values });

  const createRecord = async (kind, values) => {
    await request(FORM_META[kind].endpoint, { method: "POST", token, body: values });
    setModal("");
    setToast(`${FORM_META[kind].title.replace(/^(Add|Create|Log|Record) /, "")} saved`);
    await loadWorkspace(token, user);
  };

  const updateStatus = async (endpoint, value) => {
    try { await request(endpoint, { method: "PATCH", token, body: value }); await loadWorkspace(token, user); setToast("Record updated"); }
    catch (reason) { setToast(reason.message); }
  };

  const convertOpportunity = async (opportunityId) => {
    try {
      const result = await request(`/opportunities/${opportunityId}/convert`, { method: "POST", token });
      await loadWorkspace(token, user);
      setToast(`Converted to client organization #${result.organization_id}`);
    } catch (reason) { setToast(reason.message); }
  };

  const saveUserRoles = async (target, roleNames, isActive) => {
    await request(`/admin/users/${target.id}/roles`, { method: "PATCH", token, body: { role_names: roleNames, is_active: isActive } });
    setManagedUser(null); setToast("User access updated"); await loadWorkspace(token, user);
  };

  const refresh = () => loadWorkspace(token, user);
  const meta = PAGE_META[page] || PAGE_META.overview;
  const unreadNotifications = data.notifications.filter((item) => !item.read_at).length;

  if (booting) return <div className="screen-loader"><span className="loader-mark">H</span><span>Opening your workspace…</span></div>;
  if (!token) return <AuthScreen onLogin={authenticate} onRegister={register} />;
  if (!user) return <div className="screen-loader"><span className="loader-mark">H</span><span>Loading your profile…</span></div>;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark">H</div>
          <div><div className="brand-name">HRUTA</div><div className="brand-product">ONECRM</div></div>
          <button className="icon-button sidebar-close" aria-label="Close menu" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
        </div>
        <div className="workspace-switcher">
          <div className="workspace-avatar">H</div>
          <div className="workspace-copy"><strong>HRUTA workspace</strong><span>CRM workspace</span></div>
          <ChevronDown size={15} className="muted-icon" />
        </div>
        <nav className="main-nav" aria-label="Main navigation">
          {NAV_GROUPS.map((group) => {
            const items = group.items.filter(canAccessPage);
            if (!items.length) return null;
            return <div className="nav-group" key={group.label}>
              <div className="nav-label">{group.label}</div>
              {items.map((key) => {
                const item = PAGE_META[key]; const Icon = item.icon;
                return <button key={key} className={`nav-item ${page === key ? "active" : ""}`} onClick={() => { setPage(key); setSearch(""); setSidebarOpen(false); }}>
                  <Icon size={17} strokeWidth={1.9} /><span>{item.label}</span>
                  {key === "tasks" && data.summary?.tasks_overdue > 0 && <span className="nav-count">{data.summary.tasks_overdue}</span>}
                  {key === "notifications" && unreadNotifications > 0 && <span className="nav-count">{unreadNotifications}</span>}
                </button>;
              })}
            </div>;
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><div className="help-icon"><Sparkles size={17} /></div><strong>Make work flow</strong><p>Your customer relationships, all in one place.</p></div>
          <div className="profile-row">
            <div className="avatar avatar-small">{initials(user.full_name)}</div>
            <div className="profile-copy"><strong>{user.full_name}</strong><span>{user.roles?.[0] || "Team member"}</span></div>
            <button className="icon-button logout-button" title="Sign out" onClick={logout}><LogOut size={16} /></button>
          </div>
        </div>
      </aside>
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button menu-button" aria-label="Open menu" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{meta.label}</strong></div>
          <div className="topbar-right">
            <div className="api-status"><span className="status-dot" /> API connected</div>
            <button className="icon-button notification-button" title="Notifications" onClick={() => setPage("notifications")}><Bell size={17} />{unreadNotifications > 0 && <span className="notification-dot" />}</button>
            <button className="top-avatar" title={user.email}>{initials(user.full_name)}</button>
          </div>
        </header>

        <div className="page-content">
          {page === "overview" ? <Dashboard data={data} user={user} canSell={canSell} onNavigate={setPage} onCreate={setModal} busy={dataBusy} /> :
            page === "reports" ? <ReportsPage summary={data.reportSummary} token={token} roles={roles} /> :
            page === "notifications" ? <NotificationsPage rows={data.notifications} token={token} onReload={() => loadWorkspace(token, user)} /> :
            page === "documents" ? <DocumentsPage data={data} token={token} roles={roles} /> :
            page === "adminUsers" ? <AdminUsersPage rows={data.adminUsersData} roles={data.roles} onManage={setManagedUser} /> :
            page === "configuration" ? <ConfigurationPage rows={data.configuration} token={token} onReload={() => loadWorkspace(token, user)} /> :
            <DataPage page={page} data={data} search={search} onSearch={setSearch} onCreate={() => setModal(meta.action)} canCreate={canCreatePage(page)} busy={dataBusy} onRefresh={refresh} onUpdateStatus={updateStatus} onRefundAction={updateStatus} onConvertOpportunity={convertOpportunity} user={user} />
          }
        </div>
      </main>

      {modal && <CreateModal kind={modal} data={data} onClose={() => setModal("")} onSubmit={createRecord} />}
      {managedUser && <RolesModal user={managedUser} roles={data.roles} onClose={() => setManagedUser(null)} onSave={saveUserRoles} />}
      {toast && <div className="toast"><CheckCircle2 size={17} />{toast}</div>}
    </div>
  );
}

function AuthScreen({ onLogin, onRegister }) {
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    setNotice("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const email = String(form.get("email") || "").trim().toLowerCase();
    const password = String(form.get("password") || "");
    try {
      if (mode === "register") {
        await onRegister({ full_name: String(form.get("full_name") || "").trim(), email, password });
        setMode("login"); setError(""); setNotice("Account created. Sign in with your new credentials.");
        formElement.reset();
      } else await onLogin(email, password);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };

  return <div className="auth-page">
    <div className="auth-art">
      <div className="auth-art-grid" />
      <div className="auth-brand"><div className="brand-mark">H</div><div><div className="brand-name">HRUTA</div><div className="brand-product">ONECRM</div></div></div>
      <div className="auth-pitch"><span className="eyebrow light-eyebrow"><Sparkles size={13} /> YOUR BUSINESS, IN SYNC</span>
        <h1>Relationships<br />move business<br /><em>forward.</em></h1>
        <p>Keep every lead, conversation and next step moving in one connected workspace.</p>
        <div className="auth-illustration"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><Target size={30} /></div><span className="orbit-node node-a"><UsersRound size={16} /></span><span className="orbit-node node-b"><Activity size={16} /></span><span className="orbit-node node-c"><BriefcaseBusiness size={16} /></span></div>
      </div>
      <div className="auth-foot"><span>© {new Date().getFullYear()} HRUTA OneCRM</span><span>Focused on what matters</span></div>
    </div>
    <div className="auth-panel">
      <div className="auth-panel-top"><span>Welcome to your workspace</span><ShieldCheck size={17} /></div>
      <div className="auth-form-wrap">
        <div className="auth-mobile-brand"><div className="brand-mark">H</div><strong>HRUTA <span>ONECRM</span></strong></div>
        <span className="eyebrow">{mode === "login" ? "YOUR CRM, READY" : "GET STARTED"}</span>
        <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
        <p className="auth-subtitle">{mode === "login" ? "Sign in to pick up right where you left off." : "Join your team’s customer workspace."}</p>
        {error && <div className="form-error">{error}</div>}
        {notice && <div className="form-notice"><CheckCircle2 size={15} />{notice}</div>}
        <form onSubmit={submit} className="auth-form">
          {mode === "register" && <label className="field-label">Full name<div className="input-wrap"><UserRound size={17} /><input name="full_name" placeholder="Your name" autoComplete="name" minLength={2} required /></div></label>}
          <label className="field-label">Work email<div className="input-wrap"><Mail size={17} /><input name="email" type="email" placeholder="you@company.com" autoComplete="email" required /></div></label>
          <label className="field-label">Password<div className="input-wrap"><LockKeyhole size={17} /><input name="password" type="password" placeholder="At least 10 characters" minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} required /></div></label>
          <button className="primary-button auth-submit" disabled={busy}>{busy ? <span className="button-loader" /> : mode === "login" ? <>Sign in <ArrowRight size={17} /></> : <>Create account <ArrowRight size={17} /></>}</button>
        </form>
        <div className="auth-switch">{mode === "login" ? "New to OneCRM?" : "Already have an account?"}<button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setNotice(""); }}>{mode === "login" ? "Create account" : "Sign in"}</button></div>
        {mode === "register" && <div className="role-note"><ShieldCheck size={15} /> New accounts start with the Employee / Intern role.</div>}
      </div>
      <div className="auth-panel-foot"><span>Secure team access</span><span>·</span><span>One place to move forward</span></div>
    </div>
  </div>;
}

function Dashboard({ data, user, canSell, onNavigate, onCreate, busy }) {
  const summary = data.summary || {};
  const firstName = user.full_name?.split(" ")[0] || "there";
  const stats = [
    { label: "Total leads", value: summary.leads_total ?? "—", change: "In your pipeline", icon: UsersRound, tone: "blue", href: "leads" },
    { label: "Open opportunities", value: summary.opportunities_open ?? "—", change: formatMoney(summary.open_pipeline_value), icon: BriefcaseBusiness, tone: "violet", href: "opportunities" },
    { label: "Follow-ups due", value: summary.leads_due_for_follow_up ?? "—", change: "Ready for your attention", icon: CalendarDays, tone: "amber", href: "leads" },
    { label: "Open tasks", value: summary.tasks_open ?? "—", change: `${summary.tasks_overdue ?? 0} overdue`, icon: ListTodo, tone: "green", href: "tasks" },
  ];
  if (summary.applications_active !== null && summary.applications_active !== undefined) stats.push({ label: "Active internships", value: summary.applications_active, change: `${summary.applications_completed ?? 0} completed`, icon: GraduationCap, tone: "violet", href: "applications" });
  if (summary.training_enrollments !== null && summary.training_enrollments !== undefined) stats.push({ label: "Training learners", value: summary.training_enrollments, change: `${summary.training_active_batches ?? 0} active batches`, icon: UsersRound, tone: "blue", href: "enrollments" });
  if (summary.active_partners !== null && summary.active_partners !== undefined) stats.push({ label: "Active partners", value: summary.active_partners, change: "Across partnerships", icon: Handshake, tone: "green", href: "partners" });
  if (summary.projects_active !== null && summary.projects_active !== undefined) stats.push({ label: "Active projects", value: summary.projects_active, change: `${summary.milestones_overdue ?? 0} overdue milestones`, icon: FolderKanban, tone: "amber", href: "projects" });
  if (summary.invoiced_amount !== null && summary.invoiced_amount !== undefined) stats.push({ label: "Outstanding invoices", value: formatMoney(summary.outstanding_amount), change: `${formatMoney(summary.payments_received)} received`, icon: CircleDollarSign, tone: "blue", href: "invoices" });
  const recentLeads = data.leads.slice(0, 5);
  const nextTasks = data.tasks.filter((task) => !["done", "cancelled"].includes(task.status)).slice(0, 4);
  return <>
    <div className="welcome-banner">
      <div className="welcome-copy"><span className="eyebrow"><span className="sparkle-dot" /> {new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" }).format(new Date()).toUpperCase()}</span>
        <h1>{greeting()}, {firstName}<span className="wave">✦</span></h1><p>Here’s what’s happening across your workspace today.</p>
        <div className="welcome-actions"><button className="primary-button" onClick={() => onCreate(canSell ? "lead" : "task")}><Plus size={17} />{canSell ? "Add a lead" : "New task"}</button><button className="soft-button" onClick={() => onNavigate("tasks")}>View my tasks <ArrowRight size={15} /></button></div>
      </div>
      <div className="welcome-visual"><div className="welcome-orbit orbit-a" /><div className="welcome-orbit orbit-b" /><div className="welcome-center"><Target size={34} /></div><div className="welcome-float float-one"><span className="tiny-avatar avatar-orange">A</span><span>New lead</span><span className="float-plus">+</span></div><div className="welcome-float float-two"><span className="float-check"><Check size={13} /></span><span>Task completed</span></div><div className="welcome-spark spark-one">✳</div><div className="welcome-spark spark-two">✦</div></div>
    </div>
    <section className="section-block">
      <div className="section-heading"><div><span className="eyebrow">YOUR SNAPSHOT</span><h2>Workspace overview</h2></div><button className="text-button" onClick={() => onNavigate("reports")}>View reports <ArrowRight size={15} /></button></div>
      <div className="stats-grid">{stats.map(({ label, value, change, icon: Icon, tone, href }, index) => <button className="stat-card" key={label} onClick={() => onNavigate(href)}>
        <div className={`stat-icon ${tone}`}><Icon size={19} /></div><div className="stat-label">{label}</div><div className="stat-value">{busy ? <span className="skeleton skeleton-number" /> : value}</div><div className="stat-foot"><span className={`stat-trend ${index === 2 ? "trend-warm" : ""}`}>{index === 2 ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}{change}</span><ArrowRight className="stat-arrow" size={15} /></div>
      </button>)}</div>
    </section>
    <div className="dashboard-columns">
      <section className="panel recent-panel"><div className="panel-heading"><div><span className="eyebrow">PIPELINE</span><h2>Recent leads</h2></div><button className="panel-link" onClick={() => onNavigate("leads")}>See all <ArrowRight size={14} /></button></div>
        {recentLeads.length ? <div className="lead-list">{recentLeads.map((lead, index) => <div className="lead-row" key={lead.id}><div className={`avatar lead-avatar avatar-color-${index % 4}`}>{initials(displayName(lead))}</div><div className="lead-main"><strong>{displayName(lead)}</strong><span>{lead.organization_name || "No organization"}</span></div><span className={`status-pill ${statusTone(lead.status)}`}>{lead.status}</span></div>)}</div> : <EmptyState icon={Target} title="Your pipeline starts here" text="Add a lead to keep new opportunities moving." action={canSell ? "Add your first lead" : undefined} onAction={canSell ? () => onCreate("lead") : undefined} />}
      </section>
      <section className="panel tasks-panel"><div className="panel-heading"><div><span className="eyebrow">STAY ON TRACK</span><h2>Up next</h2></div><button className="panel-link" onClick={() => onNavigate("tasks")}>All tasks <ArrowRight size={14} /></button></div>
        {nextTasks.length ? <div className="task-list">{nextTasks.map((task) => <div className="task-row" key={task.id}><div className={`task-check ${task.status === "done" ? "checked" : ""}`}>{task.status === "done" && <Check size={12} />}</div><div className="task-main"><strong>{task.title}</strong><span><Clock3 size={12} />{task.due_at ? niceDate(task.due_at) : "No due date"}</span></div><span className={`priority-dot priority-${statusTone(task.priority)}`} title={task.priority} /></div>)}</div> : <EmptyState icon={ListTodo} title="A clear day ahead" text="Create a task to capture your next step." action="Create a task" onAction={() => onCreate("task")} />}
        <div className="task-footer"><div className="task-footer-icon"><CheckCircle2 size={16} /></div><span><strong>{summary.tasks_overdue ?? 0} overdue</strong><small>Keep your follow-ups on track</small></span><button className="icon-button" onClick={() => onNavigate("tasks")} aria-label="View tasks"><ArrowRight size={16} /></button></div>
      </section>
    </div>
    <div className="dashboard-bottom"><div className="bottom-card pipeline-card"><div className="bottom-card-icon"><CircleDollarSign size={19} /></div><div><span className="eyebrow">OPEN PIPELINE</span><strong>{formatMoney(summary.open_pipeline_value)}</strong><small>Across active opportunities</small></div><button onClick={() => onNavigate("opportunities")}><ArrowUpRight size={17} /></button></div><div className="bottom-card insight-card"><div className="insight-spark"><Sparkles size={19} /></div><div><span className="eyebrow">A LITTLE MOMENTUM</span><strong>Every good relationship starts with a conversation.</strong><small>Log a call, meeting or note to keep the context close.</small></div><button onClick={() => onCreate("activity")}><Plus size={17} /></button></div></div>
  </>;
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

const TABLES = {
  leads: { columns: [["Name", (r) => displayName(r), "person"], ["Organization", (r) => r.organization_name || "—"], ["Email", (r) => r.email || "—"], ["Interest", (r) => r.interest || "—"], ["Status", (r) => r.status, "status"], ["Priority", (r) => r.priority, "status"]] },
  organizations: { columns: [["Organization", (r) => r.name, "person"], ["Type", (r) => r.organization_type || "—", "status"], ["Industry", (r) => r.industry || "—"], ["Website", (r) => r.website || "—"], ["Added", (r) => niceDate(r.created_at)]] },
  contacts: { columns: [["Contact", (r) => displayName(r), "person"], ["Email", (r) => r.email || "—"], ["Phone", (r) => r.phone || "—"], ["Organization ID", (r) => r.organization_id || "—"], ["Designation", (r) => r.designation || "—"]] },
  opportunities: { columns: [["Opportunity", (r) => r.name, "person"], ["Stage", (r) => r.stage, "status"], ["Expected value", (r) => formatMoney(r.expected_value)], ["Close date", (r) => niceDate(r.expected_close_date)], ["Owner ID", (r) => r.owner_id || "—"]] },
  tasks: { columns: [["Task", (r) => r.title, "person"], ["Status", (r) => r.status, "status"], ["Priority", (r) => r.priority, "status"], ["Due date", (r) => niceDate(r.due_at)], ["Assignee ID", (r) => r.assignee_id || "—"]] },
  activities: { columns: [["Activity", (r) => r.subject, "person"], ["Type", (r) => r.activity_type, "status"], ["Outcome", (r) => r.outcome || "—"], ["Occurred", (r) => niceDate(r.occurred_at)], ["Linked record", (r) => r.lead_id ? `Lead #${r.lead_id}` : r.opportunity_id ? `Opportunity #${r.opportunity_id}` : r.contact_id ? `Contact #${r.contact_id}` : "—"]] },
  invoices: { columns: [["Invoice", (r) => r.invoice_number, "person"], ["Description", (r) => r.description], ["Amount", (r) => formatMoney(r.amount)], ["Received", (r) => formatMoney(r.received)], ["Outstanding", (r) => formatMoney(r.outstanding)], ["Status", (r) => r.status, "status"]] },
  payments: { columns: [["Payment", (r) => `#${r.id}`, "person"], ["Invoice ID", (r) => r.invoice_id], ["Amount", (r) => formatMoney(r.amount)], ["Date", (r) => niceDate(r.payment_date)], ["Method", (r) => r.method], ["Status", (r) => r.status, "status"]] },
  proposals: { columns: [["Proposal", (r) => r.title, "person"], ["Opportunity ID", (r) => r.opportunity_id], ["Version", (r) => r.version], ["Amount", (r) => formatMoney(r.amount)], ["Status", (r) => r.status, "status"], ["Created", (r) => niceDate(r.created_at)]] },
  refunds: { columns: [["Refund", (r) => `#${r.id}`, "person"], ["Payment ID", (r) => r.payment_id], ["Amount", (r) => formatMoney(r.amount)], ["Reason", (r) => r.reason], ["Status", (r) => r.status, "status"], ["Requested", (r) => niceDate(r.created_at)]] },
  programs: { columns: [["Program", (r) => r.name, "person"], ["Domain", (r) => r.domain || "—"], ["Duration", (r) => r.duration_weeks ? `${r.duration_weeks} weeks` : "—"], ["Mode", (r) => r.mode || "—", "status"], ["Fee", (r) => formatMoney(r.fee)]] },
  applications: { columns: [["Student", (r) => r.full_name, "person"], ["Email", (r) => r.email], ["College", (r) => r.college_name || "—"], ["Program ID", (r) => r.program_id || "—"], ["Status", (r) => r.status, "status"], ["Applied", (r) => niceDate(r.applied_at)]] },
  interviews: { columns: [["Application ID", (r) => r.application_id, "person"], ["Interviewer ID", (r) => r.interviewer_id || "—"], ["Scheduled", (r) => niceDate(r.scheduled_at)], ["Status", (r) => r.status, "status"], ["Rating", (r) => r.rating || "—"], ["Feedback", (r) => r.feedback || "—"]] },
  allocations: { columns: [["Application ID", (r) => r.application_id, "person"], ["Team", (r) => r.team_name], ["Coordinator ID", (r) => r.coordinator_id || "—"], ["Assigned", (r) => niceDate(r.assigned_at)], ["Notes", (r) => r.notes || "—"]] },
  internAttendance: { columns: [["Application ID", (r) => r.application_id, "person"], ["Date", (r) => niceDate(r.attendance_date)], ["Status", (r) => r.status, "status"], ["Notes", (r) => r.notes || "—"]] },
  internTasks: { columns: [["Task", (r) => r.title, "person"], ["Application ID", (r) => r.application_id], ["Due date", (r) => niceDate(r.due_date)], ["Status", (r) => r.status, "status"]] },
  certificates: { columns: [["Certificate", (r) => r.certificate_number || `#${r.id}`, "person"], ["Application ID", (r) => r.application_id], ["Type", (r) => r.certificate_type, "status"], ["Issued", (r) => niceDate(r.issued_at)], ["Status", (r) => r.status, "status"]] },
  courses: { columns: [["Course", (r) => r.name, "person"], ["Price", (r) => formatMoney(r.price)], ["Syllabus", (r) => r.syllabus_reference || "—"], ["Status", (r) => r.is_active ? "active" : "inactive", "status"]] },
  trainers: { columns: [["Trainer", (r) => r.name, "person"], ["Email", (r) => r.email || "—"], ["Phone", (r) => r.phone || "—"], ["Expertise", (r) => r.expertise || "—"]] },
  batches: { columns: [["Batch", (r) => r.name, "person"], ["Course ID", (r) => r.course_id], ["Trainer ID", (r) => r.trainer_id || "—"], ["Mode", (r) => r.mode || "—", "status"], ["Starts", (r) => niceDate(r.start_date)], ["Status", (r) => r.status, "status"]] },
  enrollments: { columns: [["Learner", (r) => r.student_name, "person"], ["Email", (r) => r.student_email], ["Batch ID", (r) => r.batch_id], ["Status", (r) => r.status, "status"], ["Enrolled", (r) => niceDate(r.enrolled_at)]] },
  sessions: { columns: [["Session", (r) => r.title, "person"], ["Batch ID", (r) => r.batch_id], ["Starts", (r) => niceDate(r.starts_at)], ["Meeting link", (r) => r.meeting_url || "—"]] },
  trainingAttendance: { columns: [["Session ID", (r) => r.session_id, "person"], ["Enrollment ID", (r) => r.enrollment_id], ["Recorded", (r) => niceDate(r.recorded_at)], ["Status", (r) => r.status, "status"]] },
  assessments: { columns: [["Assessment", (r) => r.title, "person"], ["Course ID", (r) => r.course_id || "—"], ["Maximum score", (r) => r.max_score]] },
  results: { columns: [["Assessment ID", (r) => r.assessment_id, "person"], ["Enrollment ID", (r) => r.enrollment_id], ["Score", (r) => r.score], ["Submitted", (r) => niceDate(r.submitted_at)]] },
  feedback: { columns: [["Learner", (r) => r.enrollment_id ? `Enrollment #${r.enrollment_id}` : `Application #${r.application_id}`, "person"], ["Rating", (r) => r.rating], ["Comments", (r) => r.comments || "—"], ["Submitted", (r) => niceDate(r.created_at)]] },
  partners: { columns: [["Partner", (r) => r.name, "person"], ["Type", (r) => r.partner_type || "—"], ["Organization ID", (r) => r.organization_id || "—"], ["Contact ID", (r) => r.primary_contact_id || "—"], ["Status", (r) => r.status, "status"]] },
  partnershipActivities: { columns: [["Activity", (r) => r.title, "person"], ["Partner ID", (r) => r.partner_id], ["Type", (r) => r.activity_type, "status"], ["Date", (r) => niceDate(r.activity_date)], ["Details", (r) => r.description || "—"]] },
  agreements: { columns: [["Agreement", (r) => r.title, "person"], ["Partner ID", (r) => r.partner_id], ["Status", (r) => r.status, "status"], ["Starts", (r) => niceDate(r.start_date)], ["Ends", (r) => niceDate(r.end_date)]] },
  projects: { columns: [["Project", (r) => r.name, "person"], ["Client ID", (r) => r.organization_id || "—"], ["Manager ID", (r) => r.project_manager_id], ["Status", (r) => r.status, "status"], ["Target end", (r) => niceDate(r.target_end_date)]] },
  milestones: { columns: [["Milestone", (r) => r.title, "person"], ["Project ID", (r) => r.project_id], ["Due date", (r) => niceDate(r.due_date)], ["Status", (r) => r.status, "status"]] },
  projectUpdates: { columns: [["Project ID", (r) => r.project_id, "person"], ["Progress", (r) => `${r.progress_percent ?? 0}%`], ["Update", (r) => r.update_text], ["Posted", (r) => niceDate(r.created_at)]] },
  projectTasks: { columns: [["Task", (r) => r.title, "person"], ["Project ID", (r) => r.project_id], ["Assignee ID", (r) => r.assignee_id || "—"], ["Due", (r) => niceDate(r.due_at)], ["Priority", (r) => r.priority, "status"], ["Status", (r) => r.status, "status"]] },
  auditLogs: { columns: [["Action", (r) => r.action, "person"], ["User ID", (r) => r.user_id], ["Record", (r) => `${r.entity_type} #${r.entity_id}`], ["Details", (r) => r.details || "—"], ["When", (r) => niceDate(r.created_at)]] },
};

const STATUS_EDIT = {
  leads: { endpoint: (r) => `/leads/${r.id}`, field: "status", options: ["new", "contacted", "qualified", "unqualified", "converted", "lost"] },
  opportunities: { endpoint: (r) => `/opportunities/${r.id}`, field: "stage", options: ["qualification", "proposal", "negotiation", "won"] },
  tasks: { endpoint: (r) => `/tasks/${r.id}`, field: "status", options: ["todo", "in_progress", "blocked", "done", "cancelled"] },
  proposals: { endpoint: (r) => `/sales/proposals/${r.id}`, field: "status", options: ["draft", "sent", "accepted", "rejected"] },
  applications: { endpoint: (r) => `/internships/applications/${r.id}`, field: "status", options: ["applied", "interview_scheduled", "selected", "offered", "onboarding", "active", "completed", "rejected", "withdrawn"] },
  interviews: { endpoint: (r) => `/internships/interviews/${r.id}`, field: "status", options: ["scheduled", "completed", "cancelled", "no_show"] },
  internTasks: { endpoint: (r) => `/internships/tasks/${r.id}`, field: "status", options: ["assigned", "in_progress", "submitted", "reviewed", "completed"] },
  certificates: { endpoint: (r) => `/internships/certificates/${r.id}`, field: "status", options: ["pending", "approved", "issued", "cancelled"] },
  batches: { endpoint: (r) => `/training/batches/${r.id}`, field: "status", options: ["planned", "active", "completed", "cancelled"] },
  enrollments: { endpoint: (r) => `/training/enrollments/${r.id}`, field: "status", options: ["enrolled", "in_progress", "completed", "withdrawn"] },
  partners: { endpoint: (r) => `/partners/${r.id}`, field: "status", options: ["prospect", "active", "inactive", "expired"] },
  agreements: { endpoint: (r) => `/partnership-agreements/${r.id}`, field: "status", options: ["draft", "active", "renewal_due", "expired", "terminated"] },
  projects: { endpoint: (r) => `/projects/${r.id}`, field: "status", options: ["planned", "active", "on_hold", "completed", "cancelled"] },
  milestones: { endpoint: (r) => `/project-milestones/${r.id}`, field: "status", options: ["pending", "in_progress", "completed", "delayed"] },
  projectTasks: { endpoint: (r) => `/project-tasks/${r.id}`, field: "status", options: ["todo", "in_progress", "blocked", "done", "cancelled"] },
};

const CREATE_LABELS = { lead: "Add lead", organization: "Add organization", contact: "Add contact", opportunity: "New opportunity", task: "New task", activity: "Log activity", invoice: "New invoice", payment: "Record payment" };

function DataPage({ page, data, search, onSearch, onCreate, canCreate, busy, onRefresh, onUpdateStatus, onRefundAction, onConvertOpportunity, user }) {
  const meta = PAGE_META[page];
  const Icon = meta.icon;
  const searchRef = useRef(null);
  const rows = data[meta.key] || [];
  const columns = TABLES[page]?.columns || [];
  const createLabel = CREATE_LABELS[meta.action] || FORM_META[meta.action]?.title || "New record";
  useEffect(() => {
    const handleShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault(); searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);
  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return rows;
    return rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query));
  }, [rows, search]);
  return <>
    <div className="data-page-head"><div><span className="eyebrow">YOUR WORKSPACE / {meta.label.toUpperCase()}</span><h1>{meta.title}</h1><p>Manage and keep track of {meta.label.toLowerCase()} in your workspace.</p></div>{canCreate && <button className="primary-button" onClick={onCreate}><Plus size={17} />{createLabel}</button>}</div>
    <div className="table-toolbar"><div className="search-box"><Search size={16} /><input ref={searchRef} value={search} onChange={(event) => onSearch(event.target.value)} placeholder={`Search ${meta.label.toLowerCase()}…`} /><kbd>⌘ K</kbd></div><div className="toolbar-actions"><span className="result-count">{filteredRows.length} {filteredRows.length === 1 ? "record" : "records"}</span><button className="filter-button" onClick={onRefresh} disabled={busy}><RefreshCw className={busy ? "spin-icon" : ""} size={14} /><span>{busy ? "Refreshing" : "Refresh"}</span></button></div></div>
    <div className="table-panel"><div className="table-scroll"><table><thead><tr>{columns.map(([label]) => <th key={label}>{label}</th>)}{["refunds", "opportunities"].includes(page) && <th>Actions</th>}</tr></thead><tbody>
      {filteredRows.map((row) => { const edit = STATUS_EDIT[page]; return <tr key={row.id}>{columns.map(([label, value, type]) => { const cell = value(row); const editable = edit && label.toLowerCase() === (edit.field === "stage" ? "stage" : "status") && onUpdateStatus;
        return <td key={label}>{editable ? <select className="inline-status" aria-label={`Update ${label} for record ${row.id}`} value={row[edit.field] || ""} onChange={(event) => onUpdateStatus(edit.endpoint(row), { [edit.field]: event.target.value })}>{[...new Set([row[edit.field], ...edit.options].filter(Boolean))].map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}</select> : type === "status" ? <span className={`status-pill ${statusTone(String(cell))}`}>{cell || "—"}</span> : type === "person" ? <div className="table-person"><span className="table-person-avatar">{initials(String(cell))}</span><strong>{cell}</strong></div> : <span className="table-cell-text">{cell}</span>}</td>;
      })}{page === "refunds" && <td><div className="row-actions">{row.status === "requested" && ["Super Admin", "Management"].some((r) => user?.roles?.includes(r)) && <><button className="soft-button compact" onClick={() => onRefundAction(`/refunds/${row.id}/approve`, {})}>Approve</button><button className="soft-button compact danger-text" onClick={() => { const reason = window.prompt("Why is this refund being rejected?"); if (reason?.trim()) onRefundAction(`/refunds/${row.id}/reject`, { reason: reason.trim() }); }}>Reject</button></>}{row.status === "approved" && ["Super Admin", "Management", "Finance / Accounts"].some((r) => user?.roles?.includes(r)) && <button className="soft-button compact" onClick={() => onRefundAction(`/refunds/${row.id}/process`, {})}>Mark processed</button>}</div></td>}{page === "opportunities" && <td><div className="row-actions">{row.stage === "won" && <button className="soft-button compact" onClick={() => onConvertOpportunity(row.id)}>Convert to client</button>}{!["won", "lost"].includes(row.stage) && <button className="soft-button compact danger-text" onClick={() => { const reason = window.prompt("Why was this opportunity lost?"); if (reason?.trim()) onUpdateStatus(`/opportunities/${row.id}`, { stage: "lost", lost_reason: reason.trim() }); }}>Mark lost</button>}</div></td>}</tr>; })}
      {!filteredRows.length && <tr><td colSpan={columns.length + (["refunds", "opportunities"].includes(page) ? 1 : 0)}><div className="table-empty"><div className="empty-icon"><Icon size={21} /></div><strong>{search ? "No matching records" : `No ${meta.label.toLowerCase()} yet`}</strong><span>{search ? "Try a different search term." : "New records you add will show up here."}</span>{!search && canCreate && <button className="soft-button" onClick={onCreate}><Plus size={15} />Create the first one</button>}</div></td></tr>}
    </tbody></table></div><div className="table-foot"><span>Showing {filteredRows.length} of {rows.length} records</span><span className="table-foot-right"><span className="live-dot" />Live from OneCRM API</span></div></div>
  </>;
}

function ReportsPage({ summary = {}, token, roles }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const has = (...allowed) => roles.some((role) => allowed.includes(role));
  const datasets = [
    ...(has("Super Admin", "Management", "Sales / Business Development") ? ["leads", "opportunities"] : []),
    ...(has("Super Admin", "Management", "Internship Coordinator") ? ["applications"] : []),
    ...(has("Super Admin", "Management", "Training Coordinator") ? ["enrollments"] : []),
    ...(has("Super Admin", "Management", "Project / Team Manager") ? ["projects"] : []),
    ...(has("Super Admin", "Management", "Finance / Accounts") ? ["invoices"] : []),
  ];
  const metrics = [
    ["Total leads", summary.leads_total], ["Leads with next action", summary.leads_with_next_action],
    ["Open opportunities", summary.opportunities_open], ["Pipeline value", formatMoney(summary.pipeline_value)],
    ["Active applications", summary.applications_active], ["Completed applications", summary.applications_completed],
    ["Training enrollments", summary.training_enrollments], ["Overdue tasks", summary.tasks_overdue],
    ["Active projects", summary.projects_active],
    ...(summary.finance_visible ? [["Invoiced", formatMoney(summary.invoiced_amount)], ["Payments received", formatMoney(summary.payments_received)]] : []),
  ];
  const download = async (dataset) => {
    setBusy(dataset); setError("");
    try {
      const response = await fetch(`${API_BASE}/reports/export/${dataset}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || `Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = url; link.download = `hruta-${dataset}.csv`; link.click(); URL.revokeObjectURL(url);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(""); }
  };
  return <>
    <div className="data-page-head"><div><span className="eyebrow">YOUR WORKSPACE / INSIGHTS</span><h1>Reports & exports</h1><p>See the records your role can access and download a CSV for further analysis.</p></div></div>
    <div className="report-metric-grid">{metrics.map(([label, value]) => <div className="report-metric" key={label}><span>{label}</span><strong>{value === undefined || value === null ? "—" : value}</strong></div>)}</div>
    <section className="panel report-export-panel"><div className="panel-heading"><div><span className="eyebrow">DATA EXPORT</span><h2>Download CSV files</h2></div><FileSpreadsheet size={21} /></div>
      <p className="muted-copy">Exports follow the same access rules as the CRM and include up to 10,000 records.</p>
      {error && <div className="form-error">{error}</div>}
      <div className="export-list">{datasets.length ? datasets.map((dataset) => <div className="export-row" key={dataset}><div><strong>{dataset[0].toUpperCase() + dataset.slice(1)}</strong><span>Comma-separated values</span></div><button className="soft-button" onClick={() => download(dataset)} disabled={Boolean(busy)}>{busy === dataset ? <span className="button-loader" /> : <Download size={15} />}Download</button></div>) : <div className="table-empty"><strong>No exports available</strong><span>Your current role has no enabled CSV exports.</span></div>}</div>
    </section>
  </>;
}

function NotificationsPage({ rows, token, onReload }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const unread = rows.filter((row) => !row.read_at);
  const act = async (work) => {
    setBusy(true); setError("");
    try { await work(); await onReload(); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  const markAllRead = () => act(() => Promise.all(unread.map((row) => request(`/notifications/${row.id}`, { method: "PATCH", token, body: { is_read: true } }))));
  return <>
    <div className="data-page-head"><div><span className="eyebrow">YOUR WORKSPACE / UPDATES</span><h1>Notifications</h1><p>Follow up on assigned work and due reminders.</p></div><div className="head-actions"><button className="soft-button" disabled={busy} onClick={() => act(() => request("/notifications/refresh-reminders", { method: "POST", token }))}><RefreshCw size={15} />Refresh reminders</button>{unread.length > 0 && <button className="primary-button" disabled={busy} onClick={markAllRead}><Check size={15} />Mark all read</button>}</div></div>
    {error && <div className="form-error">{error}</div>}
    <section className="panel notification-list">{rows.length ? rows.map((row) => <article className={`notification-row ${row.read_at ? "notification-read" : ""}`} key={row.id}><div className="notification-symbol"><Bell size={17} /></div><div className="notification-copy"><strong>{row.title}</strong><p>{row.message}</p><span>{niceDate(row.created_at)}{row.related_type ? ` · ${row.related_type.replaceAll("_", " ")}` : ""}</span></div><div className="notification-actions">{!row.read_at ? <button className="soft-button compact" disabled={busy} onClick={() => act(() => request(`/notifications/${row.id}`, { method: "PATCH", token, body: { is_read: true } }))}>Mark read</button> : <span className="read-label">Read</span>}</div></article>) : <div className="table-empty"><div className="empty-icon"><Bell size={21} /></div><strong>You're all caught up</strong><span>New task and follow-up reminders will appear here.</span></div>}</section>
  </>;
}

function AdminUsersPage({ rows, roles, onManage }) {
  return <>
    <div className="data-page-head"><div><span className="eyebrow">ADMINISTRATION / ACCESS</span><h1>User access</h1><p>Assign workspace roles and control which modules each person can use.</p></div><span className="result-count">{rows.length} users</span></div>
    <section className="panel admin-user-list">{rows.length ? rows.map((person) => <div className="admin-user-row" key={person.id}><div className="avatar avatar-small">{initials(person.full_name)}</div><div className="admin-user-main"><strong>{person.full_name}</strong><span>{person.email}</span><div className="role-chips">{person.roles.map((role) => <span key={role}>{role}</span>)}</div></div><span className={`status-pill ${person.is_active ? "green" : "red"}`}>{person.is_active ? "active" : "disabled"}</span><button className="soft-button" onClick={() => onManage(person)}><Pencil size={14} />Manage access</button></div>) : <div className="table-empty"><strong>No users found</strong><span>Registered users appear here.</span></div>}</section>
    <div className="admin-note"><ShieldCheck size={16} />{roles.length} roles are available. Registration assigns the basic Employee / Intern role by default.</div>
  </>;
}

function RolesModal({ user, roles, onClose, onSave }) {
  const [selected, setSelected] = useState(user.roles || []);
  const [active, setActive] = useState(Boolean(user.is_active));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await onSave(user, selected, active); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="create-modal access-modal" role="dialog" aria-modal="true" aria-labelledby="access-title">
    <div className="modal-head"><div><span className="eyebrow">ADMIN / ROLE ASSIGNMENT</span><h2 id="access-title">Manage user access</h2></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button></div>
    <p className="modal-intro">{user.full_name}<br /><span>{user.email}</span></p>{error && <div className="form-error modal-error">{error}</div>}
    <form onSubmit={submit}><div className="role-checkbox-list">{roles.map((role) => <label className="role-checkbox" key={role.id}><input type="checkbox" checked={selected.includes(role.name)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, role.name] : current.filter((name) => name !== role.name))} /><span><strong>{role.name}</strong><small>{role.name === "Super Admin" ? "Full system administration" : "Access based on assigned module"}</small></span></label>)}</div>
      <label className="active-toggle"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Account enabled</label><div className="modal-actions"><button type="button" className="soft-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy || !selected.length}>{busy ? <span className="button-loader" /> : <><Check size={15} />Save access</>}</button></div>
    </form>
  </section></div>;
}

function ConfigurationPage({ rows, token, onReload }) {
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [value, setValue] = useState("{}");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const edit = (row) => { setKey(row.key); setDescription(row.description || ""); setValue(JSON.stringify(row.value || {}, null, 2)); setNotice(""); };
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const parsed = JSON.parse(value);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Settings value must be a JSON object.");
      await request(`/admin/configuration/${encodeURIComponent(key.trim())}`, { method: "PUT", token, body: { value: parsed, description: description.trim() || null } });
      setNotice("Setting saved."); await onReload();
    } catch (reason) { setError(reason instanceof SyntaxError ? "Enter valid JSON for the setting value." : reason.message); }
    finally { setBusy(false); }
  };
  return <>
    <div className="data-page-head"><div><span className="eyebrow">ADMINISTRATION / WORKFLOW</span><h1>Workflow settings</h1><p>Store approved CRM workflow options as structured settings.</p></div></div>
    <div className="configuration-layout"><section className="panel config-form-panel"><div className="panel-heading"><div><span className="eyebrow">SETTING</span><h2>{rows.some((row) => row.key === key) ? "Edit setting" : "Add setting"}</h2></div><Settings size={20} /></div>
      {error && <div className="form-error">{error}</div>}{notice && <div className="form-success">{notice}</div>}
      <form className="record-form" onSubmit={save}><label className="field-label">Key<input value={key} onChange={(event) => setKey(event.target.value)} placeholder="e.g. crm.follow_up_days" required minLength={2} /></label><label className="field-label">Description<input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What this setting controls" /></label><label className="field-label">Value (JSON object)<textarea className="json-editor" value={value} onChange={(event) => setValue(event.target.value)} rows={7} required /></label><div className="modal-actions"><button type="button" className="soft-button" onClick={() => { setKey(""); setDescription(""); setValue("{}"); }}>Clear</button><button className="primary-button" disabled={busy || !key.trim()}>{busy ? <span className="button-loader" /> : <><Check size={15} />Save setting</>}</button></div></form>
    </section><section className="panel config-list-panel"><div className="panel-heading"><div><span className="eyebrow">SAVED SETTINGS</span><h2>Configuration</h2></div><span className="result-count">{rows.length} items</span></div>{rows.length ? rows.map((row) => <button className="config-row" key={row.key} onClick={() => edit(row)}><span><strong>{row.key}</strong><small>{row.description || "No description"}</small><code>{JSON.stringify(row.value)}</code></span><Pencil size={15} /></button>) : <div className="table-empty"><strong>No settings yet</strong><span>New configuration items will appear here.</span></div>}</section></div>
  </>;
}

const DOCUMENT_TYPES = [
  ["lead", "Leads", ["Super Admin", "Management", "Sales / Business Development"], "leads", (r) => displayName(r)],
  ["opportunity", "Opportunities", ["Super Admin", "Management", "Sales / Business Development"], "opportunities", (r) => r.name],
  ["organization", "Organizations", ["Super Admin", "Management", "Sales / Business Development"], "organizations", (r) => r.name],
  ["contact", "Contacts", ["Super Admin", "Management", "Sales / Business Development"], "contacts", (r) => displayName(r)],
  ["proposal", "Sales proposals", ["Super Admin", "Management", "Sales / Business Development"], "proposals", (r) => r.title],
  ["application", "Internship applications", ["Super Admin", "Management", "Internship Coordinator"], "applications", (r) => r.full_name],
  ["certificate", "Certificates", ["Super Admin", "Management", "Internship Coordinator"], "certificates", (r) => r.certificate_number || `Certificate #${r.id}`],
  ["course", "Courses", ["Super Admin", "Management", "Training Coordinator"], "courses", (r) => r.name],
  ["batch", "Training batches", ["Super Admin", "Management", "Training Coordinator"], "batches", (r) => r.name],
  ["enrollment", "Enrollments", ["Super Admin", "Management", "Training Coordinator"], "enrollments", (r) => r.student_name],
  ["session", "Training sessions", ["Super Admin", "Management", "Training Coordinator"], "sessions", (r) => r.title],
  ["partner", "Partners", ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"], "partners", (r) => r.name],
  ["partnership_activity", "Partner activities", ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"], "partnershipActivities", (r) => r.title],
  ["agreement", "Agreements", ["Super Admin", "Management", "Sales / Business Development", "Internship Coordinator"], "agreements", (r) => r.title],
  ["project", "Projects", ["Super Admin", "Management", "Project / Team Manager"], "projects", (r) => r.name],
  ["milestone", "Milestones", ["Super Admin", "Management", "Project / Team Manager"], "milestones", (r) => r.title],
  ["project_update", "Project updates", ["Super Admin", "Management", "Project / Team Manager"], "projectUpdates", (r) => r.update_text],
  ["project_task", "Project tasks", ["Super Admin", "Management", "Project / Team Manager", "Employee / Intern"], "projectTasks", (r) => r.title],
  ["invoice", "Invoices", ["Super Admin", "Management", "Finance / Accounts"], "invoices", (r) => r.invoice_number],
  ["payment", "Payments", ["Super Admin", "Management", "Finance / Accounts"], "payments", (r) => `Payment #${r.id}`],
  ["refund", "Refunds", ["Super Admin", "Management", "Finance / Accounts"], "refunds", (r) => `Refund #${r.id}`],
];

function DocumentsPage({ data, token, roles }) {
  const types = DOCUMENT_TYPES.filter(([, , allowed]) => roles.some((role) => allowed.includes(role)));
  const [type, setType] = useState(types[0]?.[0] || "");
  const [entityId, setEntityId] = useState("");
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const selectedType = types.find(([value]) => value === type) || types[0];
  const records = selectedType ? (data[selectedType[3]] || []) : [];
  useEffect(() => { if (types.length && !types.some(([value]) => value === type)) setType(types[0][0]); }, [type, types]);
  const load = useCallback(async () => {
    if (!type || !entityId) { setDocuments([]); return; }
    try { setDocuments(await request(`/documents?entity_type=${encodeURIComponent(type)}&entity_id=${encodeURIComponent(entityId)}`, { token })); }
    catch (reason) { setDocuments([]); setError(reason.message); }
  }, [type, entityId, token]);
  useEffect(() => { setError(""); load(); }, [load]);
  const upload = async (event) => {
    event.preventDefault(); const formElement = event.currentTarget; if (!file || !entityId) return;
    setBusy(true); setError(""); setNotice("");
    const multipart = new FormData(); multipart.append("entity_type", type); multipart.append("entity_id", entityId); multipart.append("file", file);
    try { await request("/documents", { method: "POST", token, multipart }); setFile(null); formElement.reset(); setNotice("Document uploaded."); await load(); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  const download = async (record) => {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/documents/${record.id}/download`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) { const payload = await response.json().catch(() => null); throw new Error(payload?.detail || `Download failed (${response.status})`); }
      const url = URL.createObjectURL(await response.blob()); const link = document.createElement("a"); link.href = url; link.download = record.file_name; link.click(); URL.revokeObjectURL(url);
    } catch (reason) { setError(reason.message); }
  };
  return <>
    <div className="data-page-head"><div><span className="eyebrow">YOUR WORKSPACE / RECORD FILES</span><h1>Documents & evidence</h1><p>Attach approved files to CRM records and download them when needed.</p></div></div>
    <div className="documents-layout"><section className="panel document-upload-panel"><div className="panel-heading"><div><span className="eyebrow">PRIVATE FILE STORAGE</span><h2>Upload a document</h2></div><FileText size={20} /></div>
      {error && <div className="form-error">{error}</div>}{notice && <div className="form-success">{notice}</div>}
      {types.length ? <form className="record-form" onSubmit={upload}><label className="field-label">Record type<select value={type} onChange={(event) => { setType(event.target.value); setEntityId(""); }} required>{types.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="field-label">Record<select value={entityId} onChange={(event) => setEntityId(event.target.value)} required><option value="">Select a record</option>{records.map((row) => <option value={row.id} key={row.id}>#{row.id} · {String(selectedType[4](row)).slice(0, 90)}</option>)}</select></label><label className="field-label">File (PDF, DOCX, XLSX, PNG, JPG)<input type="file" accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label><small className="muted-copy">Maximum file size: 10 MB.</small><button className="primary-button" disabled={busy || !entityId || !file}>{busy ? <span className="button-loader" /> : <><Plus size={15} />Upload file</>}</button></form> : <div className="table-empty"><strong>No record types available</strong><span>Your assigned role has no document permissions.</span></div>}
    </section><section className="panel document-list-panel"><div className="panel-heading"><div><span className="eyebrow">LINKED FILES</span><h2>Record documents</h2></div><button className="icon-button" aria-label="Refresh documents" onClick={load}><RefreshCw size={16} /></button></div>{!entityId ? <div className="table-empty"><strong>Select a record</strong><span>Its linked files will appear here.</span></div> : documents.length ? documents.map((record) => <div className="document-row" key={record.id}><div className="document-icon"><FileText size={18} /></div><div className="document-copy"><strong>{record.file_name}</strong><span>{(Number(record.size_bytes || 0) / 1024).toFixed(1)} KB · {niceDate(record.created_at)}</span></div><button className="soft-button compact" onClick={() => download(record)}><Download size={14} />Download</button></div>) : <div className="table-empty"><strong>No files linked</strong><span>Uploaded documents for this record will show up here.</span></div>}</section></div>
  </>;
}

function EmptyState({ icon: Icon, title, text, action, onAction }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={20} /></div><strong>{title}</strong><p>{text}</p>{action && <button className="soft-button" onClick={onAction}>{action} <ArrowRight size={14} /></button>}</div>;
}

function CreateModal({ kind, onClose, onSubmit, data }) {
  const config = FORM_META[kind];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!config) return null;
  const relatedRows = {
    organizations: data.organizations.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    leads: data.leads.map((row) => ({ value: row.id, label: `#${row.id} · ${displayName(row)}` })),
    opportunities: data.opportunities.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    contacts: data.contacts.map((row) => ({ value: row.id, label: `#${row.id} · ${displayName(row)}` })),
    invoices: data.invoices.map((row) => ({ value: row.id, label: `#${row.id} · ${row.invoice_number} (${formatMoney(row.outstanding)})` })),
    payments: data.payments.map((row) => ({ value: row.id, label: `#${row.id} · ${formatMoney(row.amount)} · ${row.method}` })),
    programs: data.programs.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    applications: data.applications.map((row) => ({ value: row.id, label: `#${row.id} · ${row.full_name}` })),
    courses: data.courses.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    trainers: data.trainers.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    batches: data.batches.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    enrollments: data.enrollments.map((row) => ({ value: row.id, label: `#${row.id} · ${row.student_name}` })),
    sessions: data.sessions.map((row) => ({ value: row.id, label: `#${row.id} · ${row.title}` })),
    assessments: data.assessments.map((row) => ({ value: row.id, label: `#${row.id} · ${row.title}` })),
    partners: data.partners.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    projects: data.projects.map((row) => ({ value: row.id, label: `#${row.id} · ${row.name}` })),
    users: data.directoryUsers.map((row) => ({ value: row.id, label: `#${row.id} · ${row.full_name} · ${(row.roles || []).join(", ")}` })),
  };
  const fields = config.fields.map((field) => field.relation
    ? { ...field, type: "select", options: relatedRows[field.relation] || [] }
    : field);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
      const values = {};
    for (const field of fields) {
      const raw = String(form.get(field.name) ?? "").trim();
      if (!raw) continue;
      values[field.name] = field.type === "number" || field.relation ? Number(raw) : raw;
    }
    if (kind === "activity" && !values.lead_id && !values.opportunity_id && !values.contact_id) {
      setError("Link this activity to a lead, opportunity, or contact."); setBusy(false); return;
    }
    try { await onSubmit(kind, values); }
    catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="create-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-head"><div><span className="eyebrow">ONECRM / NEW RECORD</span><h2 id="modal-title">{config.title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button></div>
      <p className="modal-intro">Add the details below. You can update this record later.</p>
      {error && <div className="form-error modal-error">{error}</div>}
      <form className="record-form" onSubmit={submit}><div className="record-fields">
        {fields.map((field) => <label className={`field-label ${field.wide ? "field-wide" : ""}`} key={field.name}>{field.label}{field.required && <span className="required-mark"> *</span>}
          {field.type === "textarea" ? <textarea name={field.name} placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`} required={field.required} rows={3} /> : field.type === "select" ? <select name={field.name} defaultValue={field.default || (field.relation ? "" : field.options[0])} required={field.required}>{field.relation && <option value="">Select {field.label.toLowerCase()}</option>}{field.options.map((option) => typeof option === "string" ? <option value={option} key={option}>{option.replaceAll("_", " ")}</option> : <option value={option.value} key={option.value}>{option.label}</option>)}</select> : <input name={field.name} type={field.type || "text"} placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`} required={field.required} min={field.type === "number" ? 0 : undefined} step={field.name === "expected_value" || field.name === "amount" ? "0.01" : undefined} />}
        </label>)}
      </div><div className="modal-actions"><button type="button" className="soft-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? <span className="button-loader" /> : <><Send size={15} />Save record</>}</button></div></form>
    </section>
  </div>;
}

export default App;

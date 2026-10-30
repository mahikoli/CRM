# HRUTA OneCRM — Business CRM

A full-stack CRM starter based on the HRUTA OneCRM proposal. The API uses FastAPI, SQLAlchemy 2, JWT bearer authentication and role-based access controls; the web app uses React and Vite.

## Included modules

- **CRM and sales:** leads, organizations, contacts, opportunity pipeline, stage history, proposal tracking and won-deal conversion.
- **Internships:** programs, applications, interviews, team allocations, attendance, intern tasks and certificates.
- **Training coordination:** courses, trainers, batches, enrollments, sessions, attendance, assessments, results and learner feedback. This coordinates LMS activity; it is not a replacement LMS.
- **Partnerships:** partner records, activities and agreements.
- **Projects:** project ownership, milestones, progress updates and assigned tasks.
- **Finance:** invoices, payments, balance checks, refund requests, approval and processing.
- **Workspace tools:** in-app notifications, role-aware reports and CSV exports, private record documents, workflow settings and admin audit/user-role management.
- **Foundation:** user registration and login, seeded role names, dashboard KPIs, validation and SQLAlchemy models.

External LMS/accounting/WhatsApp integrations, outbound email or messaging automation, AI features, password reset, and deployment-specific cloud file storage are not included. The proposal treats external systems as integrations to approve separately and advises against duplicating full LMS/accounting products.

File uploads are stored under the configured private upload directory (`UPLOAD_DIR`, defaults to `private_uploads/`). Allowed uploads are PDF, DOCX, XLSX, PNG and JPG, up to 10 MB each. The local SQLite database is convenient for development, not a production deployment plan.

## 1. Database

Local development uses SQLite in `hruta_onecrm.db` by default, so no database server setup is needed. To use PostgreSQL or Supabase, set `DATABASE_URL` in `.env` to a `postgresql+psycopg://...` connection string for your database.

## 2. Install and configure

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to replace `SECRET_KEY` with a long random secret. Set `DATABASE_URL` only when using PostgreSQL or Supabase; URL-encode special characters in database passwords. Supabase connection options depend on whether you use direct or pooler connections. Do not commit `.env` to GitHub.

The API uses SQLAlchemy models in `app/models.py` as its executable schema. `sql/postgresql_schema.sql` is a separate proposal design with UUID-based IDs; do not run it against the same database used by this API.

## 3. Run

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive Swagger API documentation. Health check: `GET /health`.

## Frontend

The React frontend is the sibling folder `../frontend/`. Start it in a second terminal from the project root:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The frontend connects to the API at `http://127.0.0.1:8000/api/v1` by default. Set `VITE_API_BASE_URL` in `frontend/.env` to change it.

The app creates missing tables and seeds role names at startup for local development. `create_all` does not migrate existing table columns; use reviewed Alembic migrations for schema changes in a deployed environment. Before production, configure TLS, hosting, backups, private object storage, and organization-approved retention controls.

## 4. Bootstrap the first administrator

Public registration intentionally assigns only `Employee / Intern`; it does not allow a caller to grant themselves admin permissions. Create a user through `/api/v1/auth/register`, then promote the first administrator through a trusted database console once, for example:

```sql
INSERT INTO user_roles (user_id, role_id)
SELECT :user_id, id FROM roles WHERE name = 'Super Admin'
ON CONFLICT DO NOTHING;
```

Use a parameterized query and replace `:user_id` with the verified account ID. Restrict access to the database console.

## Authentication

`POST /api/v1/auth/login` accepts form fields `username` (the user's email) and `password`. It returns a bearer access token. Click **Authorize** in Swagger and enter the token as prompted.

## Main API routes

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Obtain access token |
| GET | `/api/v1/auth/me` | Current user and roles |
| POST / GET | `/api/v1/leads` | Create/list leads; filters and pagination |
| GET / PATCH | `/api/v1/leads/{lead_id}` | View/update a lead |
| POST / GET | `/api/v1/organizations` | Create/list organizations |
| POST / GET | `/api/v1/contacts` | Create/list contacts |
| POST / GET | `/api/v1/opportunities` | Create/list sales opportunities |
| PATCH | `/api/v1/opportunities/{opportunity_id}` | Update sales stage/details |
| POST / GET | `/api/v1/activities` | Record/list calls, meetings, emails, notes |
| POST / GET | `/api/v1/tasks` | Create/list tasks; supports overdue filter |
| PATCH | `/api/v1/tasks/{task_id}` | Update task |
| GET | `/api/v1/dashboard/summary` | Role-scoped core CRM KPIs |
| POST / GET | `/api/v1/invoices` | Finance-role invoice operations |
| POST / GET | `/api/v1/payments` | Record/list payments |
| GET / POST / PATCH | `/api/v1/internships/...` | Internship programs, applications, interviews, allocations, attendance, tasks and certificates |
| GET / POST / PATCH | `/api/v1/training/...` | Courses, batches, enrollments, sessions, attendance, assessments, results and feedback |
| GET / POST / PATCH | `/api/v1/partners...`, `/api/v1/projects...` | Partnerships and project delivery |
| GET / POST / PATCH | `/api/v1/refunds...` | Finance refund workflow |
| GET / POST | `/api/v1/documents` | Upload/list private files linked to permitted CRM records |
| GET | `/api/v1/reports/summary`, `/api/v1/reports/export/{dataset}` | Role-scoped reporting and CSV export |
| GET / PATCH / PUT | `/api/v1/admin/...` | Super Admin user access, audit log and workflow settings |

## Important design decisions

- A lead, opportunity, contact, invoice and payment are separate records, not one combined table.
- Money uses `NUMERIC(12,2)` / `Decimal`, not floating point.
- Lists use pagination where appropriate.
- API permission checks are server-side; frontend hiding is not security.
- Finance endpoints are restricted to Finance / Accounts, Management, or Super Admin; refund decisions require Management or Super Admin.
- Non-manager users see only their own leads/opportunities and their assigned/created tasks in list endpoints.
- This is a development starter, not production-certified. Add rate limiting, password reset, refresh/revocation strategy, strict field/state validation, migration tooling, automated tests, and organization-approved privacy/retention controls before deployment.

# HRUTA OneCRM

Full-stack CRM workspace with a React frontend and FastAPI backend.

## Project layout

```text
hruta_onecrm_backend/
├── backend/
│   ├── app/                 # FastAPI application and routers
│   ├── sql/                 # PostgreSQL reference schema
│   ├── .env.example         # Backend configuration template
│   ├── requirements.txt     # Python dependencies
│   └── README.md            # Backend setup and API details
├── frontend/
│   ├── src/                 # React application
│   ├── package.json
│   └── package-lock.json
└── .gitignore
```

The existing local SQLite database was kept at `backend/hruta_onecrm.db`.

## Run locally on Windows

Start the API in the first terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set SECRET_KEY in .env before using accounts
uvicorn app.main:app --reload
```

Start the React app in a second terminal from the project root:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal. The API Swagger page is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and its health check is [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

For backend feature scope, database details, API routes, and first-admin bootstrap instructions, see [backend/README.md](backend/README.md).

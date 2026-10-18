# 📬 Recruiter Outreach Engine

A local workspace for finding possible recruiter leads, checking email signals, and drafting outreach using candidate-supplied facts. Discovery and mailbox checks are uncertain; they do not guarantee address ownership or delivery.

Built step-by-step from scratch using **project-based learning principles**.

## Current behavior (phases 1–3)

- Search failures and empty searches return no leads, with warnings. No sample recruiters are substituted. Email patterns remain guesses; `recommended_email` is unset until ownership can be established.
- Resume parsing leaves unknown facts empty and returns warnings. Confirm the profile before using it. Pitch requests require `candidate`, `candidate_name` and `target_role`; optional skills and projects are not invented.
- Writing review and refinement use fixed rules, not Gemini. Review never authorizes sending. `unchecked_guidelines` lists rules needing manual review. Unsupported editing instructions are reported instead of being claimed as completed.
- Outbox mode `draft` is the default. `simulate` creates a `simulated` record with no send timestamp and no impact on sent counts. `live_send` returns **503** because no mail provider is connected.
- Confirmed profiles, discovery snapshots, drafts, simulations and history are saved to SQLite and survive restarts. No worker sends queued messages. Hosted mode uses a single-owner password gate. Multi-user accounts and real email delivery are not implemented.

### Dashboard workflow

Start the server and open **http://127.0.0.1:8000/dashboard**. The dashboard uses React + Vite. FastAPI serves the compiled frontend and API together. Run `npm ci --prefix frontend` and `npm run build --prefix frontend` before starting the server.

1. Paste or open a Markdown resume, extract details, then correct and confirm your profile. You can also enter your details directly.
2. Search for contacts or add a known contact from your research. Manual entries and generated email patterns remain unverified.
3. Select a contact and generate a starting draft from your saved profile. Edit the message, choose or enter an address, and confirm you reviewed it before saving.
4. Open **Saved drafts** to reopen and edit a note, inspect counts and see recent activity. Saved records survive server restarts; unsaved editor text does not.

Drafts retain their profile and discovery IDs. Retrying a new workflow save with the same `request_id` returns the existing draft; changing its contents under that ID returns 409. Editing requires `expected_version`: a stale edit returns 409 instead of overwriting a newer revision. Reopen the draft to load the latest version before retrying. Recipient review is a human acknowledgment, not proof of email ownership.

| Workflow action | Endpoint |
|---|---|
| Add a manually researched contact | `POST /api/v1/workflow/contacts` |
| Generate using saved profile and lead | `POST /api/v1/workflow/preview` |
| Save a linked draft with retry protection | `POST /api/v1/workflow/drafts` |
| Edit an existing draft | `PATCH /api/v1/outbox/items/{id}` |

The legacy `/outbox/queue` endpoint remains available for independent drafts and simulations; workflow retry protection applies to `/workflow/drafts`. Simulation records cannot be edited. No dashboard action sends email.

### Persistent storage

SQLite is a local database file: no separate database server or extra package is needed. The default file is `data/outreach.sqlite3` under the repository, independent of the directory you start the server from. Startup creates the directory and schema automatically. Database files are excluded from Git because they contain candidate and outreach data.

| Action | Endpoint |
|---|---|
| Save a confirmed candidate profile | `POST /api/v1/profiles` (a CandidateProfile body) |
| List or reopen profiles | `GET /api/v1/profiles`, `GET /api/v1/profiles/{id}` |
| Discover and save a search snapshot | Existing `POST` or `GET /api/v1/discover-recruiters`; response adds `discovery_id` |
| List or reopen search results | `GET /api/v1/discoveries`, `GET /api/v1/discoveries/{id}` |
| Save a draft or simulation | Existing `POST /api/v1/outbox/queue` |
| Reopen one outbox item | `GET /api/v1/outbox/items/{id}` |
| Read saved activity | `GET /api/v1/history`, optionally with `record_id` |

Profiles are saved explicitly after confirmation; parsing a resume alone does not save one. Each profile save creates an immutable snapshot with a new ID. Drafts can be edited with revision checks; deletion is not implemented. Discovery snapshots preserve the search request, extracted leads, warnings and each available email probe result, including its diagnostic reason. Empty searches are also saved. Standalone email-verification requests are not saved yet. Saving a snapshot does not confirm that a person or address is genuine.

List endpoints accept `limit` (default 50, maximum 100) and `offset` (default 0). Outbox listing still supports `status`. Missing records return 404. Database failures return 503 rather than silently falling back to memory; storage setup failure stops server startup. Each saved record and its history event are written in one transaction, meaning either both are saved or neither is saved.

To choose a different database path before starting the server in PowerShell:

```powershell
$env:DATABASE_PATH = "C:\path\to\outreach.sqlite3"
$env:DAILY_SEND_LIMIT = "25"
uvicorn app.main:app --reload --port 8000
```

Use a local disk file shared by workers on the same computer. Environment settings are read directly; `.env` files are not automatically loaded. `DAILY_SEND_LIMIT` initializes the database's shared limit **only on first use**. Later workers read the stored limit instead of resetting it from their environment. A limit-editing API and atomic send reservations will be added with real delivery; this phase only persists the cap and derives sent counts from stored records using UTC dates. Simulations never count as sent.

The schema is versioned using SQLite's `user_version` (currently 1). Setup is repeatable and refuses a database created by a newer schema instead of overwriting it. For a simple backup, stop every server using the file, then copy the database to a separate safe location. Restore to a new file and select it with `DATABASE_PATH`. In-memory records from phase 1 cannot be recovered after that process has stopped.

#### Try a restart

1. In `/docs`, save a profile such as `{"candidate_name":"Jane","target_role":"Accountant","core_skills":["Excel"]}` using `POST /api/v1/profiles`.
2. Save a draft or simulation and keep its returned ID.
3. Stop and restart the server using the same database path.
4. Reopen the saved profile and outbox item by ID, then check `/api/v1/history` and `/api/v1/outbox/stats`.

### API compatibility changes

Blank/oversized fields, invalid recipient addresses, unsupported tones and malformed company domains return **422** validation errors. Parsed resume `name` and `target_role` may be `null`. High-scoring writing reviews return `Manual Review Required` instead of `Ready to Send`. Outbox statistics now include `total_simulated`.

### Verification

After installing dependencies into your virtual environment and building the frontend, run from the repository root:

```powershell
npm ci --prefix frontend
npm run build --prefix frontend
python -m unittest discover -s tests -p "test_*.py" -v
```

This runs offline smoke, regression and persistence tests with search/mail probes replaced by controlled test responses. Storage tests use temporary databases, check reopen behavior in a separate Python process, concurrent access, shared counts and rollback after failed writes. They do not alter the development database or send email. The standalone `tests/test_verifier.py` script makes live mail-server checks and is intentionally not included in this offline suite.

In the interactive API docs, submit `/api/v1/outbox/queue` with a valid recipient, name, company, subject and body. With `mode: "simulate"`, expect `status: "simulated"` and `sent_at: null`; with `mode: "live_send"`, expect 503. A blank recruiter name in `/api/v1/ai/review` should return 422, not an internal server error.

### Remaining phases

1. Improve discovery provenance and mail verification, including timeout/uncertainty handling.
2. Connect a mail provider with approval, durable scheduling, retries and duplicate prevention.
3. Add grounded AI writing support, multi-user authentication, suppression lists and deployment monitoring.

---

## 🛠️ System Architecture

- **Frontend:** React + Vite, with real database counts and a seven-day activity chart
- **Backend Framework:** FastAPI (Asynchronous Python ASGI server)
- **Data Validation:** Pydantic V2 (Strict type safety and data models)
- **Email Deliverability:** DNS MX lookups (`dnspython`) & SMTP handshake simulations
- **Async Networking:** `httpx` and `anyio`
- **Persistence:** SQLite via Python's standard library; record snapshots, indexed outbox counts and atomic history writes

---

## 🚀 Quickstart for Local Development

### 1. Prerequisites
- Python 3.12+ or 3.13+ installed.
- Git installed.
- Node.js 22.12+ and npm installed for the React frontend.

### 2. Setup Virtual Environment
```bash
# Windows
py -3.13 -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Build the dashboard
```bash
npm ci --prefix frontend
npm run build --prefix frontend
```
For frontend development, run the API on port 8000 and `npm run dev --prefix frontend` in a second terminal. Vite forwards `/api` requests to FastAPI.

### 4. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Health Check Endpoint: `http://127.0.0.1:8000/api/v1/health`


## Hosting on Vercel with PostgreSQL

The repository deploys as a FastAPI application. `vercel.json` builds the React frontend first; FastAPI serves `frontend/dist` and `/api/v1` from the same domain. Keep the Vercel root directory at the repository root and the application preset at **FastAPI**. Do not select the `frontend` folder as a separate deployment.

Vercel needs an external database: a local SQLite file is not durable storage there. Connect a PostgreSQL provider (for example Neon) from Vercel's Storage marketplace and set these environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | The provider's pooled PostgreSQL connection string with TLS enabled. Keep it secret. |
| `WORKSPACE_USERNAME` | Optional; defaults to `owner`. |
| `WORKSPACE_PASSWORD` | A unique password of at least 16 characters, set as a sensitive variable. |

The browser prompts for the workspace credentials. This is a **single-owner workspace**, not separate accounts for multiple users. Use HTTPS. The app refuses hosted data access until the database URL and password are configured. The health URL is an unauthenticated liveness check, not proof of database readiness. `/api/v1/workspace` exercises the configured database after authentication.

PostgreSQL tables and schema version are initialized transactionally on first use. Concurrent draft saves use database locks, and edits require a matching revision. Connections close after each operation; the provider's pooled URL handles connection reuse. SQLite is still the local default when `DATABASE_URL` is unset. Local records are **not automatically uploaded** to the hosted database. Use a dedicated database for this app and separate databases for preview/test environments; do not point untrusted preview branches at production data.

After adding or changing Vercel environment variables, redeploy. Open `/dashboard`, save a test profile and draft, refresh, and reopen them to check persistence. Live mail-server probes may be restricted by the host; unknown results remain unverified. Email sending is disabled.

GitHub Actions builds React and runs the Python suite against a dedicated PostgreSQL service. Locally, the three PostgreSQL integration tests skip unless `TEST_DATABASE_URL` points to a **dedicated test database**. They insert test records and verify persistence, concurrent retries, stale edits and rollback. Never use the production database for tests.

Sources: [Vercel FastAPI deployment](https://vercel.com/docs/frameworks/backend/fastapi), [PostgreSQL integrations](https://vercel.com/docs/postgres).

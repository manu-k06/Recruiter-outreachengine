# 📬 Recruiter Outreach Engine

An automated, intelligent command center designed to safely discover tech recruiters, verify email deliverability (preventing bounces), and generate hyper-tailored outreach pitches.

Built step-by-step from scratch using **project-based learning principles**.

---

## 🛠️ System Architecture

- **Backend Framework:** FastAPI (Asynchronous Python ASGI server)
- **Data Validation:** Pydantic V2 (Strict type safety and data models)
- **Email Deliverability:** DNS MX lookups (`dnspython`) & SMTP handshake simulations
- **Async Networking:** `httpx` and `anyio`

---

## 🚀 Quickstart for Local Development

### 1. Prerequisites
- Python 3.12+ or 3.13+ installed.
- Git installed.

### 2. Setup Virtual Environment
```bash
# Windows
py -3.13 -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
- Health Check Endpoint: `http://127.0.0.1:8000/api/v1/health`

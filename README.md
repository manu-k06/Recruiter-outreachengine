# 📬 Recruiter Outreach Engine

A backend prototype for finding possible recruiter leads, checking email signals, and drafting outreach using candidate-supplied facts. Discovery and mailbox checks are uncertain; they do not guarantee address ownership or delivery.

Built step-by-step from scratch using **project-based learning principles**.

## Current behavior (phase 1)

- Search failures and empty searches return no leads, with warnings. No sample recruiters are substituted. Email patterns remain guesses; `recommended_email` is unset until ownership can be established.
- Resume parsing leaves unknown facts empty and returns warnings. Confirm the profile before using it. Pitch requests require `candidate`, `candidate_name` and `target_role`; optional skills and projects are not invented.
- Writing review and refinement use fixed rules, not Gemini. Review never authorizes sending. `unchecked_guidelines` lists rules needing manual review. Unsupported editing instructions are reported instead of being claimed as completed.
- Outbox mode `draft` is the default. `simulate` creates a `simulated` record with no send timestamp and no impact on sent counts. `live_send` returns **503** because no mail provider is connected.
- Drafts and simulations exist only in memory and disappear on restart. No worker sends queued messages. There is no authentication or production deployment setup yet; use locally for development.

### API compatibility changes

Blank/oversized fields, invalid recipient addresses, unsupported tones and malformed company domains return **422** validation errors. Parsed resume `name` and `target_role` may be `null`. High-scoring writing reviews return `Manual Review Required` instead of `Ready to Send`. Outbox statistics now include `total_simulated`.

### Verification

After installing dependencies into your virtual environment, run from the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

This runs the offline smoke and regression tests with search/mail probes replaced by controlled test responses. It does not send email. The standalone `tests/test_verifier.py` script makes live mail-server checks and is intentionally not included in this offline suite.

In the interactive API docs, submit `/api/v1/outbox/queue` with a valid recipient, name, company, subject and body. With `mode: "simulate"`, expect `status: "simulated"` and `sent_at: null`; with `mode: "live_send"`, expect 503. A blank recruiter name in `/api/v1/ai/review` should return 422, not an internal server error.

### Remaining phases

1. Persist profiles, leads, drafts, events and quotas in a database.
2. Connect a complete draft-first workflow and dashboard.
3. Improve discovery provenance and mail verification, including timeout/uncertainty handling.
4. Connect a mail provider with approval, durable scheduling, retries and duplicate prevention.
5. Add grounded AI writing support, authentication, suppression lists, CI and deployment monitoring.

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

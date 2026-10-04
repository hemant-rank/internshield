# InternShield 🛡️

**AI-assisted verification for internship and job offer letters.**

InternShield helps students identify potentially fraudulent internship and job offers. Users can paste offer text or upload a document, then receive a risk score, a verdict, clear red flags, and suggested next steps.

> InternShield provides automated risk signals, not legal advice. Always verify an employer independently before paying money or sharing sensitive documents.

## Features

- Analyze pasted text or upload PDF, DOCX, TXT, and common image files.
- Detect fraud indicators with a **10-rule deterministic rule engine**.
- Perform keyword-based NLP language analysis.
- Extract companies, people, dates, email addresses, and phone numbers using regex-based NER.
- Optionally check company name, website, and contact email evidence.
- Show a confidence score, verdict, triggered flags, and recommended next steps.
- Keep recent scans available in the browser session.

## How analysis works

InternShield combines three signals into one score:

| Component | Purpose | Weight |
| --- | --- | --- |
| Rule engine | Structural and known scam indicators | 30% |
| NLP classifier | Fraud and genuine-language patterns | 50% |
| Entity analysis | Extracted entities and verification signals | 20% |

### 10 rule-engine checks

1. Suspicious email domains
2. Implausible stipend amounts
3. Known fake company names
4. Missing offer-letter fields
5. Date inconsistencies
6. Poor grammar quality
7. High-pressure or urgent language
8. Generic greetings
9. Suspicious links
10. Registration-fee or payment demands

### Verdicts

| Score | Verdict |
| --- | --- |
| 75–100 | Likely Genuine |
| 45–74 | Suspicious |
| 0–44 | Likely Fake |

## Architecture

```text
Next.js 16 + React 19 frontend
              │
              ▼
      FastAPI Python backend
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  10 rules    NLP      Entity extraction

```

## Tech stack

- **Frontend:** Next.js 16, React 19, TypeScript, CSS Modules
- **Backend:** FastAPI, Pydantic, Uvicorn
- **Document processing:** pdfplumber, python-docx, Pillow, pytesseract
- **Text analysis:** textstat, rapidfuzz, regex-based entity extraction
- **Deployment:** Vercel (separate frontend and backend projects)

## Run locally

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm

### 1. Start the backend

Open a terminal at the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

The API is available at `http://127.0.0.1:8000`.

### 2. Start the frontend

Open a second terminal at the project root:

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
npm run dev
```

Open `http://localhost:3000`.

If port 8000 is unavailable, run the backend on another port (for example `8001`) and change `NEXT_PUBLIC_API_URL` to that same base URL. Do not append `/api`; the frontend adds it automatically.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/analyze` | Analyze an uploaded file or text |
| `GET` | `/api/result/{scan_id}` | Retrieve one analysis result |
| `GET` | `/api/history/{session_id}` | Retrieve session scan history |

### `POST /api/analyze` form fields

| Field | Required | Description |
| --- | --- | --- |
| `session_id` | Yes | Browser/session identifier |
| `file` | No | PDF, DOCX, TXT, or supported image |
| `text` | No | Offer letter text |
| `company_name_input` | No | Company name provided by the user |
| `company_website` | No | Company website provided by the user |
| `contact_email` | No | Contact email provided by the user |

Provide either `file` or `text`.

## Deploy on Vercel

Deploy this repository as two Vercel projects:

1. **Backend project**
   - Root Directory: `backend`
   - Framework: FastAPI/Python (auto-detected)
2. **Frontend project**
   - Root Directory: `frontend`
   - Framework: Next.js

**Live application:** [https://internshield-v3qc.vercel.app/](https://internshield-v3qc.vercel.app/)

## Project structure

```text
internshield/
├── backend/
│   ├── data/                 # Known-company and domain data
│   ├── models/               # Pydantic schemas
│   ├── routers/              # FastAPI routes
│   ├── services/             # Extraction, rules, NLP, scoring
│   ├── main.py               # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/app/              # Pages and styles
│   ├── src/components/
│   ├── src/lib/api.ts        # Frontend API client
│   └── package.json
└── README.md
```

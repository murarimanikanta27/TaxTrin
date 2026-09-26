# TaxTrin — Proof of Concept

A working proof of concept for **TaxTrin**, a Trinidad & Tobago tax preparation and BIR e-Tax
integration SaaS. Built to validate the tax engine, the e-Tax export formats, and the core user
workflows described in the project brief, ahead of a full production build.

Backend: **Python 3.11 + FastAPI + SQLAlchemy** (in a venv). Frontend: **React 18 + Vite +
TypeScript + Tailwind CSS**.

Read [`NOTES.md`](NOTES.md) for exactly which tax figures are confirmed against an official
source vs. derived/assumed, and which BIR e-Tax file formats are real vs. best-effort placeholders.
That document also answers most of the open questions raised in the discovery-phase client email.

## What's in this POC

- A dynamic tax engine (NIS, PAYE, Health Surcharge, Business Levy, Green Fund Levy, Corporate
  Tax, VAT, wear-and-tear/capital allowances) driven entirely by an admin-editable database table,
  not hardcoded constants.
- Role-based accounts: Individual, Sole Trader, Corporate, Firm (multi-client), and System Admin.
- A Free/Pro/Enterprise/Firm feature-gating matrix that's actually enforced by the API (not just
  documented): Free tier is capped at 1 TD4/year and can't export e-Tax files or download official
  PDFs; VAT 200 filing requires Pro+; Form 500 corporate filing requires Enterprise/Firm.
- A guided tax interview wizard with a live refund/balance-due indicator.
- Drag-and-drop TD4 certificate OCR: upload a photo/image (PNG, JPEG, WEBP, TIFF, BMP) or a **PDF**
  (single- or multi-page, native-text or scanned) of a TD4, get extracted fields pre-filled into an
  editable correction form, review/fix anything wrong, then save. PDFs with a real text layer are
  read directly (instant, exact); scanned/image-only PDF pages fall back to Tesseract OCR
  automatically, page by page. TD4s saved this way are tagged "Scanned" in the UI so they're
  distinguishable from manually-entered records.
- TD4 CRUD, individual (Form 440), corporate (Form 500), VAT 200, and payroll (PAYE/NIS/Health
  Surcharge) flows.
- A BIR e-Tax Export Center: generates the **exact** TD4 Supplementary CSV format published by
  IRD, plus best-effort VAT 200 CSV and non-logged-in return XML/JSON exports (clearly flagged as
  unverified — see NOTES.md).
- TaxTrin-branded PDF summaries for Form 440, Form 500, VAT 200, payment vouchers, and payroll
  summaries.
- 98 backend tests covering the tax engine, e-Tax export formatting, PDF generation, tier-gating
  enforcement, and OCR/PDF field extraction (including native-text PDFs, scanned PDFs, and
  multi-page PDFs).

## Prerequisites

- Python 3.11+ (tested on 3.11.9)
- Node.js 18+ (tested on Node 24)
- No database server required by default — SQLite works out of the box; PostgreSQL is supported
  and recommended beyond a quick trial (see the Database section below).
- **Tesseract OCR** (only needed for the drag-and-drop TD4 scanning feature; every other feature
  works without it):
  - Windows: `winget install --id UB-Mannheim.TesseractOCR`, then confirm
    `backend/app/config.py`'s `tesseract_cmd` points at the installed
    `tesseract.exe` (defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe`).
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`
  - On macOS/Linux, `pytesseract` finds `tesseract` on PATH automatically; `tesseract_cmd` only
    matters on Windows.

## Backend setup (everything runs inside a venv)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Optional: copy .env.example to .env if you want to override defaults
# (SQLite + a POC-only JWT secret are used out of the box)
Copy-Item .env.example .env

# Seed the 2026 tax configuration and demo accounts (idempotent, safe to re-run)
.\.venv\Scripts\python.exe -m scripts.seed

# Run the API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The API is now at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

### Backend tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

### Demo accounts (seeded automatically)

All use the password `TaxTrin2026!`.

| Email | Role | Tier |
|---|---|---|
| `employee@example.tt` | Individual (PAYE employee) | Free |
| `soletrader@example.tt` | Sole Trader | Pro |
| `corporate@example.tt` | Corporate | Enterprise |
| `firmadmin@ctap.tt` | Firm Admin | Firm |
| `staff@ctap.tt` | Firm Staff | Firm |
| `admin@taxtrin.tt` | System Admin | Enterprise |

The firm admin/staff accounts come with two pre-created firm-managed clients so the multi-client
portal has something to show immediately.

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so
run the backend first (or alongside).

### Frontend build & typecheck

```powershell
cd frontend
npm run typecheck   # tsc -b --noEmit
npm run build        # production build to frontend/dist
```

## Project structure

```
backend/
  app/
    models/            SQLAlchemy models (User, Firm, Client, TaxYearConfig, TD4Input,
                        IndividualReturn, CorporateReturn, VAT200Return, PayrollRun/Line,
                        TaxSchedule, ETaxExportLog)
    services/
      tax_engine.py     Low-level statutory calculations (NIS, PAYE, Health Surcharge,
                        Business/Green Fund Levy, Corporate Tax, VAT, wear & tear)
      return_engine.py   Composes tax_engine into full Form 440 / 500 / VAT 200 computations
      payroll_engine.py  Per-pay-period NIS/Health Surcharge/PAYE for payroll runs
      etax_export.py    BIR e-Tax file generation (TD4 CSV, VAT200 CSV, non-logged-in XML/JSON)
      pdf_service.py    reportlab PDF generation for all printable summaries
      ocr.py            Tesseract-based TD4 certificate OCR + heuristic field extraction
      auth.py           Password hashing (bcrypt) + JWT issuing/verification
      entitlements.py   Free/Pro/Enterprise/Firm feature-gating matrix
    routers/            FastAPI route handlers (auth, clients, admin, td4, returns, payroll,
                        etax_export)
    seed_data.py        The single source of truth for the 2026 tax year constants
  scripts/seed.py       Seeds the DB with TaxYearConfig(2026) + demo accounts
  tests/                pytest suite (39 tax engine + 16 e-Tax export + 11 PDF + 9 entitlements
                        + 23 OCR/PDF-extraction tests)

frontend/
  src/
    lib/                api.ts (typed API client), AuthContext, ClientContext, types.ts
    components/         AppShell (nav + client switcher), ProtectedRoute, ui.tsx primitives,
                        TD4OCRUpload (drag-and-drop scan + manual-correction form)
    pages/              Login, Register, Dashboard, Clients, Wizard, CorporateReturn,
                        VAT200, Payroll, ExportCenter, AdminTaxConfig
```

## Database: SQLite or PostgreSQL, configured entirely via `.env`

Nothing about the database engine is hardcoded — `DATABASE_URL` in `backend/.env` decides it, and
`app/database.py` reads that single value. The `psycopg[binary]` driver is already in
`requirements.txt`, so switching engines is a one-line config change, not a code change.

**SQLite** (zero setup, good for a quick trial):
```
DATABASE_URL=sqlite:///./taxtrin.db
```

**PostgreSQL** (recommended for anything beyond a quick trial):
```
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
```
Create the target database first (SQLAlchemy creates the *tables* on startup, but not the
database itself):
```powershell
psql -U postgres -c "CREATE DATABASE taxtrin;"
```

`backend/.env` is gitignored — copy `backend/.env.example` to `backend/.env` and put your real
credentials there. Never commit `.env` or put real passwords in `.env.example`.

## Known limitations of this POC

See [`NOTES.md`](NOTES.md) for the full list, but in short:

- PDF summaries are TaxTrin-branded documents with the correct figures, not pixel-accurate
  overlays of the official BIR form artwork (IRD's actual form PDFs weren't available to use as a
  template for this build).
- The VAT 200 e-Tax upload CSV and the "Non-Logged-In Return" XML/JSON exports are best-effort
  placeholders — no public BIR specification for those formats was found. Only the TD4
  Supplementary CSV format is confirmed against IRD's published guide.
- TD4 OCR uses Tesseract (a lightweight, non-ML-framework OCR engine, chosen deliberately over
  heavier GPU-oriented models for this POC) plus a heuristic label-based field parser. PDFs with a
  real text layer are read exactly (no OCR error possible); images and scanned/image-only PDF
  pages go through Tesseract, which reads clean, printed/computer-rendered text well but will
  struggle with messy handwriting or badly skewed/low-quality photos of paper certificates. Every
  extracted field is meant to be reviewed and corrected by the user before saving — treat it as a
  head start, not a guaranteed-accurate result.
- Direct BIR portal integration (an actual API call to etax.ird.gov.tt) does not exist publicly, so
  this POC — like any real implementation — can only generate files for manual upload.

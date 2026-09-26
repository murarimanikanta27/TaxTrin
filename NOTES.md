# TaxTrin POC — Research Notes, Confidence Levels & Open Questions

This document records exactly what was verified against an official/authoritative source, what
was derived or assumed, and what remains genuinely open pending information only IRD/BIR can
provide. It also directly answers the eight discovery questions raised in the original client
email, based on what this POC build was able to establish.

All figures below are for **tax year 2026** and reflect Trinidad & Tobago legislation as of the
Finance Act 2025 (effective 1 January 2026) and the National Insurance (Contribution) (Amendment)
Regulations 2025 (effective 5 January 2026).

## Confidence key

- ✅ **Verified** — confirmed against an official government source (IRD, NIBTT, the Finance Act,
  a Legal Notice, or the Income Tax/Corporation Tax Act) or cross-confirmed by two independent
  professional sources (PwC, KPMG, EY Tax Summaries).
- 🟡 **Derived** — calculated from a verified source using a documented, consistent method, but not
  itself independently published anywhere I could find.
- ❓ **Unverified / assumed** — used in the POC because the original spec asked for it, but not
  confirmed against a primary source in this research pass.

## Tax figures used in the POC (`backend/app/seed_data.py`)

| Figure | Value | Confidence | Source |
|---|---|---|---|
| Personal allowance | TT$90,000/year | ✅ | PwC Tax Summaries T&T — Individual, Deductions |
| PAYE band 1 | 25% up to TT$1,000,000 chargeable income | ✅ | PwC Tax Summaries T&T — Individual, Taxes on personal income |
| PAYE band 2 | 30% above TT$1,000,000 | ✅ | Same as above |
| NIS-deductible fraction | 70% of employee NIS, deducted before PAYE | ✅ | Workzoom T&T payroll guide, cross-confirmed by PwC's NIS employee/employer split context |
| NIS combined rate | 16.2%, effective 5 Jan 2026 | ✅ | National Insurance (Contribution) (Amendment) Regulations 2025, Legal Notice No. 487/2025 |
| NIS employer:employee split | 2:1 (10.8% : 5.4%) | ✅ | PwC (class XVI combined $508.50 = $339.00 employer + $169.50 employee) and Workzoom (10.8%/5.4%), independently agree |
| NIS earnings class XVI (top band) | employee $169.50/wk, employer $339.00/wk | ✅ | PwC Tax Summaries T&T — Individual, Other taxes (explicit split published) |
| NIS earnings classes I–XV | employee/employer weekly amounts | 🟡 | **Derived**. Legal Notice 487/2025 only publishes the *combined* weekly contribution per class (the voluntary-contributor rate). I applied the confirmed 1:2 split (employee = combined ÷ 3) to all 15 remaining classes. This divides evenly to the cent for every class with zero rounding residue, and reproduces the independently-published class XVI split exactly — strong internal evidence it's correct, but classes I–XV are not *individually* published anywhere I found. |
| Health Surcharge (high) | TT$8.25/week if monthly emoluments > TT$469.99 | ✅ | ird.gov.tt/health-surcharge, cross-confirmed by PwC |
| Health Surcharge (low) | TT$4.80/week otherwise | ✅ | Same |
| Health Surcharge employer match | Employer matches the employee's contribution | ✅ | Workzoom T&T payroll guide |
| Business Levy rate | 0.6% of gross receipts | ✅ | PwC Tax Summaries T&T — Corporate & Individual, Other taxes |
| Business Levy threshold | Exempt below TT$360,000/year gross receipts | ✅ | Same |
| Business Levy new-business exemption | Exempt for first 3 years | ✅ | PwC Tax Summaries T&T — Individual, Other taxes |
| Business Levy offset | Payable only to the extent it exceeds income/corp tax | ✅ | Same |
| Green Fund Levy rate | 0.3% of gross income/receipts, non-deductible | ✅ | PwC Tax Summaries T&T — Corporate, Other taxes |
| Corporate tax — standard | 30% | ✅ | PwC Tax Summaries T&T — Corporate, Taxes on corporate income |
| Corporate tax — banks/petrochemical | 35% | ✅ | Same |
| VAT standard rate | 12.5% | ✅ | PwC Tax Summaries T&T — Corporate, Other taxes; ird.gov.tt/vat |
| VAT registration threshold | TT$600,000 / 12 months | ✅ | ird.gov.tt/VAT/registration |
| Tertiary education deduction cap | TT$72,000 (per household) | ✅ | ird.gov.tt/deductions/tertiary-education-expenses (increased from $60,000 to $72,000 effective 1 Jan 2019) |
| Pension/annuity/NIS voluntary aggregate cap | TT$60,000 | ✅ | PwC Tax Summaries T&T — Individual, Deductions |
| Charitable donation cap | 15% of total income | ✅ | Same |
| Animal shelter donation cap (individual) | Lower of 20% of income or TT$20,000 | ✅ | Same |
| Animal shelter donation cap (company) | Lower of 15% of chargeable profits or TT$100,000 | ✅ | PwC Tax Summaries T&T — Corporate, Deductions |
| First-time homeowner mortgage interest cap | TT$30,000 | ❓ | **Not independently re-verified.** This figure came from the original TaxTrin spec document, not from a primary source found in this research pass. It's plausible (historically this relief has existed in various forms) but needs confirmation against the current Income Tax Act or a current TD1/deductions guide before going into production. |
| Wear-and-tear Class A (buildings) | 10% | ✅ | PwC Tax Summaries T&T — Corporate, Deductions |
| Wear-and-tear Class B (vehicles/furniture/plant) | 30% | ✅ | Same |
| Wear-and-tear Class C (heavy equipment/computers) | 33.3% | ✅ | Same |
| Wear-and-tear Class D (extra heavy/airplanes) | 40% | ✅ | Same |
| Individual return filing deadline | 30 April following the tax year | ✅ | PwC Tax Summaries T&T — Individual, Tax administration |
| Individual late-filing penalty | TT$100 per 6 months (after 6-month grace period) | ✅ | Same |
| Corporate return filing deadline | 30 April following the accounting year | ✅ | PwC Tax Summaries T&T — Corporate, Tax administration |
| Corporate late-filing penalty | TT$1,000 per 6 months (after 6-month grace period) | ✅ | Same |
| VAT 200 filing frequency | Bimonthly, due 25th of the month following the period | ✅ | ird.gov.tt/vat-submission-of-the-vat-return |

**Rates known to change during the life of this system** (built into the "no hardcoded rates"
design specifically because of this): NIS rises to a combined 19.2% on 4 January 2027, per the
same Legal Notice 487/2025. Whoever owns the production system needs a process to update
`TaxYearConfig` (via the admin API this POC already exposes) every time NIBTT or the Finance Act
changes a number — the schema already supports having a different `TaxYearConfig` row per
`tax_year`.

## BIR e-Tax file format confidence (`backend/app/services/etax_export.py`)

| Export | Confidence | Detail |
|---|---|---|
| TD4 Supplementary CSV | ✅ **Verified** | Field order, required-ness, and every formatting rule (no header row, no quoted fields, 10-digit zero-padded BIR numbers, comma-stripping, TD4 Type enum) is transcribed directly from `ird.gov.tt/PAYE/AnnualReturn/Guide/file/supplemental`, which was fetched and read during this build. This is the one export in the system that should match a real e-Tax upload as-is. |
| VAT 200 upload CSV | ❓ **Unverified format** | No public specification for a VAT 200 e-Tax bulk-upload file was found anywhere — IRD's VAT pages document the *online form fields*, not a batch-upload file layout. The column set generated is a structural placeholder inferred from the VAT 200 return's own fields, following the same formatting conventions IRD published for TD4 (no header, 2dp amounts, no thousands separators). It is explicitly flagged `unverified_format` in the API/UI and should not be relied on for a live filing without a sample file or written spec from IRD. |
| Non-Logged-In Return (XML/JSON) | ❓ **Unverified format** | No public schema exists for e-Tax's "Prepare Return Offline" / non-logged-in submission mechanism. What's generated is an original, clearly-labeled best-effort structure (tag names mirror TaxTrin's own return model) so downstream integration code has something concrete to build/test against — not a claim that etax.ird.gov.tt will accept it. |
| Form 440 / 500 / VAT 200 PDF summaries | N/A (by design) | These are TaxTrin-branded summary documents with the correct computed figures, not overlays onto the BIR's actual form artwork. Producing a pixel-accurate Form 440/500 PDF would require the BIR's own form templates (PDF/InDesign source or precise field coordinates), which weren't available for this build. |

**Bottom line: the single format in this entire system that can be described as "matches the real
BIR e-Tax upload schema" is the TD4 Supplementary CSV.** Everything else BIR-file-shaped is a
well-structured placeholder pending real specs or sample files from IRD.

## Answers to the discovery-phase questions

Direct answers based on what this research pass was able to establish, for the questions raised in
the original client discovery email:

1. **Availability of official BIR e-Tax integration/API/file-format specifications** — Only the
   TD4 Supplementary CSV format is publicly documented (`ird.gov.tt/PAYE/AnnualReturn/Guide/*`).
   No public API exists for etax.ird.gov.tt at all — it's a browser-based portal with manual
   file-upload steps, not a system with a documented integration surface. VAT 200 and non-logged-in
   return formats have no public spec. **Recommendation: this needs to be a direct question to
   IRD/BIR (e.g. via a formal information request or an existing BIR technical contact), since it
   isn't discoverable from public sources.**
2. **Expected MVP scope and priority tax workflows** — Not something research can answer; this is
   a product decision for the client. The POC implements all workflows named in the spec at a
   basic level (individual, sole trader, corporate, VAT, payroll, firm portal) so the client can
   see relative complexity and prioritize.
3. **Applicable tax year(s) and statutory rules** — This POC targets tax year 2026 rules
   throughout, using the rates in the table above. The system is built to hold a different
   `TaxYearConfig` per year, so prior years can be added without a schema change.
4. **Availability of official Form 440, Form 500, VAT 200, TD4, and other required templates** —
   Blank historical versions of these forms are published as PDFs on ird.gov.tt (e.g. `F-440EMO--2016.pdf`,
   `F-500CTR--2017.pdf`), but they are static PDF forms, not templates/specs suitable for
   programmatic overlay, and the most recent versions weren't confirmed. Obtaining the current-year
   official templates directly from IRD (ideally as fillable PDF or with field coordinates) is
   needed before production PDF generation can match the real forms pixel-for-pixel.
5. **Availability of BIR sample XML/CSV/TXT files for testing and validation** — None found
   publicly beyond the TD4 CSV field specification itself (no actual sample *file*, just the field
   list and rules). **This is the single biggest open risk for the VAT 200 and non-logged-in
   return exports** — without a real sample file or IRD's confirmation, those formats can't be
   validated end-to-end no matter how carefully they're built.
6. **Expected deployment environment and hosting requirements** — Not researchable; a client
   decision. The POC is built to be portable (FastAPI + SQLAlchemy on SQLite or PostgreSQL, a
   static React build) and has no dependency that would lock it to a specific cloud provider.
7. **Whether direct BIR portal integration is required or whether TaxTrin should generate files
   for user upload** — Given that etax.ird.gov.tt has no public API, "generate files for manual
   upload" is the only currently-known option, and is what this POC implements. Direct portal
   integration (if IRD ever exposes one) would be a separate, larger effort requiring IRD's direct
   cooperation.
8. **Expected number of users, firms, and clients in the initial production release** — Not
   researchable; a client/business decision. The POC's RBAC and multi-tenant design (Firm → many
   Clients, staff assignment) doesn't impose an architectural ceiling at POC scale, but real
   capacity planning would need this number.

## Database configuration

`DATABASE_URL` in `backend/.env` is the single source of truth for which database engine and
credentials the app uses (see `app/config.py` / `app/database.py`) — nothing about the engine is
hardcoded anywhere else. This was verified against a real local PostgreSQL 18 instance: created a
dedicated `taxtrin` database, pointed `DATABASE_URL` at it
(`postgresql+psycopg://postgres:<password>@127.0.0.1:5432/taxtrin`), and confirmed the seed
script, all 12 tables (including the JSON-column-heavy `tax_year_configs`), login, TD4 CRUD, the
individual-return tax calculation, and TD4 CSV export all work identically to the SQLite setup.
`backend/.env` (with the real password) is gitignored; only `backend/.env.example` (with a
placeholder) is committed.

## TD4 OCR (drag-and-drop certificate scanning, images + PDFs)

Implemented via **Tesseract OCR** (through the `pytesseract` wrapper) for images, plus
**`pdfplumber`** (native text extraction) and **`pypdfium2`** (page rendering) for PDFs,
deliberately chosen over newer transformer/VLM-based OCR models (e.g. Surya OCR 2, which requires
a GPU-served vLLM or llama.cpp inference backend) since this machine has no NVIDIA GPU and the
goal was a lightweight POC dependency, not state-of-the-art accuracy. All three run entirely
in-process on CPU with no ML framework and no external system dependency beyond the Tesseract
binary itself.

Supported input types: PNG, JPEG, WEBP, TIFF, BMP images, and single- or multi-page PDFs.

PDF handling (`app/services/ocr.py::run_ocr`) is per-page and format-aware:
  - A page with a real, extractable text layer (e.g. a TD4 exported digitally, or a native PDF
    printed to PDF) is read directly via `pdfplumber` -- exact text, no OCR error possible,
    reported with `confidence: 1.0`.
  - A page with no usable text layer (i.e. it's a scanned image embedded in the PDF) is rendered
    to a bitmap via `pypdfium2` and OCR'd with Tesseract, same as a plain image upload.
  - Multi-page PDFs have every page's text concatenated in order; each page independently takes
    whichever path (native or OCR) fits it, so a PDF with some native pages and some scanned pages
    is handled correctly page-by-page.

Flow: `POST /td4/ocr` accepts the uploaded file (image or PDF, content-type or file-extension
sniffed), routes it through the logic above, and returns raw extracted text plus a best-effort
field extraction (`app/services/ocr.py::parse_td4_fields`, label-based regexes for
employer/employee name, BIR numbers, NIS number, address, and the money fields -- this parsing
step is identical regardless of whether the text came from OCR or a native PDF layer). The
frontend (`TD4OCRUpload.tsx`) shows those extracted values in an editable form next to a
confidence badge and page count, and nothing is saved as a `TD4Input` until the user
reviews/corrects the fields and clicks Save — matching the spec's "live manual correction
side-by-side" requirement. Records saved this way are tagged `source: ocr_upload` and shown with
a "Scanned" badge in the TD4 list, and the raw extracted text + confidence are stored on the
record (`ocr_raw_text`, `ocr_confidence`) for audit purposes.

**Verified**: tested end-to-end (real Tesseract/pdfplumber/pypdfium2 calls, not mocked) against
synthetically generated TD4-shaped inputs — 23 backend tests cover a plain image, a native-text
PDF, a scanned (image-only) PDF, and a multi-page PDF, confirming: native-text PDFs report
`confidence: 1.0` with exact text; scanned PDFs correctly fall through to the OCR path (a real,
sub-1.0 Tesseract confidence); every field (employer/employee name, both BIR numbers, NIS number,
address, gross earnings, NIS deducted, income tax, health surcharge) extracts correctly in every
case. A live HTTP round-trip against the running API confirmed the same for both a native-text PDF
(confidence 1.0) and a scanned PDF (confidence 0.9457), and a Puppeteer-driven browser run
confirmed the image-upload path end-to-end through the actual UI (95% confidence, all fields
correctly pre-filled, save succeeded, "Scanned" badge appeared, live tax estimate recalculated
correctly).

**Known limitation**: Tesseract (and the label-based regex parser on top of it) works well on
clean, printed/computer-rendered text and on native-text PDFs. It has not been tested against real
photographed or scanned paper TD4 certificates, which typically have skew, lighting variation,
folds, or handwritten annotations — all of which meaningfully reduce OCR accuracy for any engine.
Treat the extracted fields as a head start for manual entry, not a guaranteed-accurate result,
which is why the correction UI requires review before saving.

## Scope notes / what this POC deliberately does not implement

- **Pixel-accurate BIR form PDFs** — see the "PDF summaries" row above.
- **Client sign-off workflow enforcement** — the `Client.client_signed_off` flag exists in the data
  model and shows in the UI, but nothing currently *blocks* an export/filing action based on it.
- **Bulk TD4 Supplementary upload for an entire firm/employer in one action** — the API supports
  exporting TD4s for one client at a time; a "export every employee for this employer in one CSV"
  bulk flow would be a small, well-scoped follow-up rather than a redesign.
- **Automated tax-year rollover** — an admin currently creates a new `TaxYearConfig` row by hand
  (via the admin API) for each new year; there's no "clone last year and adjust" convenience yet.

## Corrections made during this build (kept here for transparency)

- The NIS earnings-class table was initially extracted from the wrong table in Legal Notice
  487/2025 (the *voluntary contributor* combined-rate table) and briefly mismapped as an
  employer/employee split. This was caught by writing unit tests against the one independently
  published split (class XVI) before it reached the seed data permanently, and the whole table was
  rebuilt using the confirmed 1:2 ratio. See the code comments in `backend/app/seed_data.py` for
  the full derivation.
- `find_nis_class()` initially returned the top earnings class for wages *below* the lowest
  class's minimum (a fallback that was only supposed to fire for wages *above* the highest class).
  Caught by a unit test, fixed with an explicit below-minimum guard.

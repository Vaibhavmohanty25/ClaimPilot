# ClaimPilot

**ClaimPilot** is an AI-powered, multimodal motor insurance claims processing and review platform. It ingests claim documents and vehicle damage images, reconstructs incidents, retrieves relevant policy clauses, evaluates evidence, reasons across text and images, identifies missing information, calculates a preliminary settlement position, and verifies the recommendation with a critic agent.

The system is intentionally designed as a **human-in-the-loop claims intelligence platform** rather than a fully autonomous final-approval engine.

---

## Core Capabilities

ClaimPilot supports:

- Claim forms
- Police / incident reports
- Repair estimates
- Digital PDFs
- Scanned PDFs
- Damage photographs
- Mixed evidence bundles containing documents and images
- OCR-based extraction
- Vision-language damage analysis
- Policy Retrieval-Augmented Generation (RAG)
- Cross-modal evidence reasoning
- Deterministic settlement calculation
- Agent-based orchestration
- Critic verification
- Human review escalation

---

# End-to-End Workflow

```text
Claim Upload
    |
    v
Document / Image Classification
    |
    +--------------------------+
    |                          |
    v                          v
Document Extraction        Vision Analysis
Native Text / OCR          Damage Detection
    |                          |
    +------------+-------------+
                 |
                 v
        Claim Reconstruction
                 |
                 v
           Policy Retrieval
          Qdrant Policy RAG
                 |
                 v
          Coverage Analysis
                 |
                 v
          Evidence Analysis
                 |
                 v
        Cross-Modal Reasoning
                 |
                 v
      Missing Information Agent
                 |
                 v
         Adjudication Agent
                 |
                 v
      Deterministic Settlement
                 |
                 v
            Critic Agent
                 |
                 v
       Human Review Dashboard
```

A typical evidence bundle may contain:

```text
claim_form.txt
police_report.txt
repair_estimate.txt
claim_damage.jpg
```

All uploaded files are processed as a single claim.

---

# Architecture

## Frontend

Built with:

- React
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide React

Current frontend capabilities:

- Dashboard
- Multi-file claim upload
- Drag-and-drop file intake
- File grouping and removal
- Processing state
- Claim review screen
- Coverage summary
- Evidence summary
- Visual findings
- Missing-information panel
- Cross-modal findings
- Adjudication result
- Critic verification result

Current routes:

```text
/
→ Dashboard

/claims/new
→ Multi-file claim intake

/claims/review
→ Claim investigation result
```

The frontend submits files to:

```http
POST /claims/process
```

using multipart form data:

```javascript
formData.append("files", file)
```

---

## Backend

Built with:

- FastAPI
- LangGraph
- Python
- Groq API
- Qdrant
- SentenceTransformers
- PyMuPDF
- EasyOCR
- Pillow

The backend handles:

- file intake
- document classification
- OCR
- direct text extraction
- vision analysis
- claim reconstruction
- policy retrieval
- evidence assessment
- cross-modal reasoning
- missing-information detection
- adjudication
- settlement calculation
- critic verification

---

# Agent Pipeline

## 1. Claim Reconstruction Agent

Purpose:

> Reconstruct what happened from the submitted evidence.

It extracts:

- claim type
- incident summary
- incident date
- incident location
- people involved
- vehicles involved
- reported damage
- claimed amount
- repair estimate items
- repair estimate total
- timeline
- uncertain facts
- contradictions

Example:

```json
{
  "claim_type": "Motor",
  "incident_summary": "Another vehicle struck the insured vehicle.",
  "incident_date": "10 September 2026",
  "incident_location": "Jalandhar, Punjab",
  "claimed_amount": 58000
}
```

---

## 2. Visual Evidence Agent

Purpose:

> Determine what the submitted images actually show.

It analyzes:

- visible vehicle regions
- visible damage
- damage type
- severity
- confidence
- regions not visible
- visible intact regions
- image quality issues
- visual contradictions
- visual risk flags

Example:

```json
{
  "vehicle_visible": true,
  "visible_damage": [
    {
      "region": "front_bumper",
      "damage_type": "crack",
      "severity": "severe",
      "confidence": 0.95
    }
  ]
}
```

### Important visual-evidence rule

ClaimPilot follows:

```text
NOT VISIBLE != NOT DAMAGED
```

If a region is not visible in the image, it is treated as:

```text
unverifiable
```

not automatically unsupported.

Only a clearly visible and intact region can count as visual contradiction evidence.

---

## 3. Policy Agent

Purpose:

> Determine whether the reported loss may be covered by the motor policy.

ClaimPilot uses Retrieval-Augmented Generation with Qdrant.

Current policy sections include:

1. Policy Period
2. Own Damage Coverage
3. Collision Damage
4. Exclusions
5. Deductible
6. Claim Documentation
7. Claim Assessment
8. Misrepresentation

The policy agent returns:

- coverage status
- coverage confidence
- reasoning
- deductible
- triggered exclusions
- policy evidence
- human-review requirement

Example:

```json
{
  "coverage_status": "LIKELY_COVERED",
  "coverage_confidence": 0.92,
  "applicable_deductible": 5000
}
```

---

# Policy RAG

The retrieval pipeline is:

```text
Policy text
   ↓
SentenceTransformers
   ↓
Embeddings
   ↓
Qdrant vector search
   ↓
Relevant policy sections
   ↓
LLM coverage analysis
```

Embedding model:

```text
all-MiniLM-L6-v2
```

Qdrant collection:

```text
motor_policy
```

Local development storage:

```text
.qdrant/
```

For production, a remote Qdrant deployment is recommended.

---

## 4. Evidence Analysis Agent

Purpose:

> Determine how well the submitted documents support the claim.

It evaluates:

- supported claim items
- unsupported claim items
- contradictions
- missing evidence
- risk flags
- evidence confidence
- human-review requirement

---

# Grounding Rules

Phase 2.1 introduced stricter source grounding.

If a document was uploaded and successfully parsed, downstream agents should not falsely claim that the document is missing.

Example:

```text
repair_estimate.txt uploaded and parsed
```

must not later become:

```text
Repair estimate not provided
```

The same principle applies to police reports and other processed evidence.

---

# Labour and Service-Cost Semantics

The following are treated as non-visual items:

- labour
- labor
- GST
- tax
- workshop fees
- towing
- diagnostics
- administrative charges

These items can be supported by documentary evidence and should not be rejected simply because they cannot appear in a photograph.

---

## 5. Cross-Modal Evidence Agent

Purpose:

> Compare documentary evidence with visual evidence.

Possible classifications:

- supported
- partially supported
- visually unsupported
- unverifiable

Example:

```text
Document:
Left headlamp damaged

Photo:
Left headlamp not visible

Result:
UNVERIFIABLE
```

The system also performs semantic deduplication.

For example:

```text
Left headlamp
Left headlamp assembly
```

should be treated as the same claim item.

---

## 6. Missing Information Agent

Purpose:

> Determine whether the claim has enough evidence to proceed.

Possible readiness states:

```text
READY
READY_WITH_CAUTION
NOT_READY
```

Outputs include:

- missing documents
- missing evidence
- clarifications needed
- blocking issues
- non-blocking issues
- recommended next actions
- ready-for-adjudication status

Example:

```json
{
  "claim_readiness": "NOT_READY",
  "missing_documents": [
    "Police report",
    "Repair estimate"
  ],
  "ready_for_adjudication": false
}
```

---

## 7. Adjudication Agent

Purpose:

> Produce a preliminary claim recommendation.

Possible recommendations include:

```text
APPROVE
REQUEST_MORE_INFORMATION
ESCALATE_FOR_HUMAN_REVIEW
```

Outputs include:

- coverage position
- supported damage items
- supported repair items
- disputed items
- recommended payable amount
- reasoning
- human review requirement
- next action

---

# Deterministic Settlement Calculation

Settlement arithmetic is calculated in Python where possible.

Example:

```text
Front bumper          INR 30,000
Right-front fender    INR 14,000
Bonnet repair          INR 8,000
Labour                 INR 6,000
--------------------------------
Supported total       INR 58,000

Deductible             INR 5,000
--------------------------------
Provisional payable   INR 53,000
```

ClaimPilot does not rely on the LLM alone for arithmetic.

### Readiness-aware settlement

If a claim is:

```text
NOT_READY
```

with blocking issues, the system should not expose a final payable amount.

Expected behavior:

```json
{
  "claim_readiness": "NOT_READY",
  "recommended_payable_amount": null
}
```

---

## 8. Critic Agent

Purpose:

> Independently verify the adjudication result.

The critic checks:

- policy consistency
- evidence consistency
- source grounding
- false missing-document claims
- visual interpretation
- settlement consistency
- human-review handling
- unsupported conclusions

Possible critic outcomes:

```text
VERIFIED
REVISION_REQUIRED
```

Example:

```json
{
  "verification_status": "VERIFIED",
  "adjudication_consistent_with_evidence": true,
  "adjudication_consistent_with_policy": true,
  "human_review_handled_correctly": true,
  "final_recommendation_valid": true
}
```

---

# LangGraph Workflow

Current orchestration:

```text
reconstruct
    ↓
visual
    ↓
policy
    ↓
evidence
    ↓
cross-modal
    ↓
missing-info
    ↓
adjudication
    ↓
critic
```

This keeps each responsibility isolated and makes the final result easier to audit.

---

# Document Processing

## Digital documents

```text
PDF
 ↓
PyMuPDF
 ↓
Native text extraction
```

## Scanned documents

```text
Scanned PDF / Image
        ↓
OCR
        ↓
EasyOCR
        ↓
Extracted text
```

This allows ClaimPilot to work with mixed real-world evidence.

---

# File Intelligence

Examples:

```text
claim_form.txt
→ text document

repair_estimate.pdf
→ digital or scanned document

claim_damage.jpg
→ damage photo
```

Document metadata is retained for downstream grounding.

Example:

```json
{
  "filename": "claim_damage.jpg",
  "file_type": "image",
  "content_type": "damage_photo",
  "classification_confidence": 0.75,
  "extraction_method": "vision_pending"
}
```

---

# Models

## Text model

Default:

```env
GROQ_MODEL=openai/gpt-oss-120b
```

## Vision model

Default:

```env
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

---

# Provider Retry Handling

ClaimPilot includes centralized retry handling for transient provider failures.

Retryable cases include statuses such as:

```text
408
429
500
502
503
504
```

Live runtime configuration:

```env
CLAIMPILOT_TEXT_MAX_ATTEMPTS=4
CLAIMPILOT_TEXT_429_BACKOFF=10,20,35
```

Example:

```text
Groq text-model rate limit reached.
Retrying in 10 seconds...

Retrying in 20 seconds...
```

---

# Observability

Major pipeline stages emit structured logs.

Example:

```json
{
  "stage": "evidence_node",
  "success": true,
  "claim_id": "CLM-515313A1",
  "duration_ms": 1685.36,
  "image_count": 0
}
```

Logged stages include:

- document extraction
- reconstruction
- vision
- policy
- evidence
- cross-modal analysis
- missing information
- adjudication
- critic
- overall claim processing

---

# API

## Process Claim

```http
POST /claims/process
```

Content type:

```text
multipart/form-data
```

Field:

```text
files
```

Multiple files may be submitted in one request.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/claims/process"   -F "files=@data/clean_claim/claim_form.txt"   -F "files=@data/clean_claim/police_report.txt"   -F "files=@data/clean_claim/repair_estimate.txt"   -F "files=@data/multimodal_test/claim_damage.jpg"
```

---

# Example Response Structure

```json
{
  "claim_id": "CLM-XXXXXXXX",
  "status": "critic_verification_complete",
  "phase": "2",
  "files_processed": [],
  "document_metadata": [],
  "reconstruction": {},
  "visual_analysis": {},
  "coverage_analysis": {},
  "policy_context": [],
  "evidence_analysis": {},
  "cross_modal_analysis": {},
  "missing_information": {},
  "adjudication": {},
  "critic_feedback": {}
}
```

---

# Human-in-the-Loop Frontend

The frontend converts the raw backend JSON into a review workspace.

The review screen shows:

- claim ID
- readiness
- coverage status
- evidence strength
- claimed amount
- AI recommendation
- incident reconstruction
- visual damage findings
- regions not visible
- supported evidence
- unverifiable evidence
- missing documents
- blocking issues
- recommended next actions
- preliminary adjudication
- recommended payable amount
- critic verification

The system intentionally separates:

```text
AI recommendation
```

from:

```text
human adjuster decision
```

Planned reviewer actions include:

- Approve
- Reject
- Request more information
- Escalate
- Add notes
- Override AI recommendation

---

# Project Structure

```text
ClaimPilot/
│
├── app/
│   ├── agents/
│   ├── graph/
│   ├── multimodal/
│   ├── services/
│   └── main.py
│
├── data/
│   ├── policies/
│   ├── clean_claim/
│   └── multimodal_test/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   │   ├── claims/
│   │   │   ├── layout/
│   │   │   └── ui/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewClaim.jsx
│   │   │   └── ClaimReview.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── tests/
├── requirements.txt
└── README.md
```

---

# Local Setup

## 1. Clone

```bash
git clone <YOUR_REPOSITORY_URL>
cd ClaimPilot
```

## 2. Create virtual environment

Windows:

```powershell
python -m venv venv
.
env\Scripts\Activate.ps1
```

## 3. Install backend dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure environment variables

Create:

```text
.env
```

Example:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

Optional live retry configuration:

```env
CLAIMPILOT_TEXT_MAX_ATTEMPTS=4
CLAIMPILOT_TEXT_429_BACKOFF=10,20,35
```

Do not commit `.env`.

---

# Run Backend

From the repository root:

```powershell
.
env\Scripts\python.exe -m uvicorn app.main:app
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# Run Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Create:

```text
frontend/.env
```

with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

# CORS

FastAPI should allow the frontend origin.

Example:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For deployment, add the production frontend URL.

---

# Testing

Run the full offline suite:

```powershell
.
env\Scripts\python.exe -B -m unittest discover -s tests -v
```

Phase 2.1 baseline:

```text
64 passed
1 live test skipped
```

## Grounding tests

```powershell
python -m unittest tests.test_phase21_grounding -v
```

These verify:

- uploaded documents are not falsely reported missing
- labour is not treated as visual damage
- unseen damage is treated as unverifiable
- repair estimates remain grounded
- NOT_READY claims do not expose final payable amounts
- critic catches grounding inconsistencies

## Provider hardening tests

```powershell
python -m unittest tests.test_hardening.ProviderHardeningTests -v
```

These verify:

- retry behavior
- retry limits
- timeout handling
- sanitized provider errors
- rate-limit handling

---

# Example End-to-End Outcomes

## Well-supported claim

```text
Coverage:
LIKELY_COVERED

Evidence:
STRONG

Readiness:
READY / READY_WITH_CAUTION

Recommendation:
APPROVE
or
ESCALATE_FOR_HUMAN_REVIEW

Critic:
VERIFIED
```

## Incomplete claim

```text
Coverage:
INSUFFICIENT_POLICY_EVIDENCE

Evidence:
WEAK

Readiness:
NOT_READY

Recommendation:
REQUEST_MORE_INFORMATION

Recommended payable:
null

Critic:
VERIFIED
```

---

# Deployment

## Frontend

The React frontend can be deployed on Vercel.

Recommended settings:

```text
Root Directory:
frontend

Framework:
Vite

Build Command:
npm run build

Output Directory:
dist
```

Production environment variable:

```env
VITE_API_BASE_URL=https://your-backend-domain
```

For React Router:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

## Backend

The current backend is better suited to a container-oriented host because it uses:

- PyTorch
- EasyOCR
- SentenceTransformers
- Qdrant
- multi-stage LLM processing
- potentially long-running requests

Recommended production architecture:

```text
Vercel
   ↓
React Frontend

Container Host
   ↓
FastAPI + LangGraph

Qdrant Cloud
   ↓
Policy Vector Database

Groq
   ↓
Text + Vision Inference
```

---

# Production Considerations

Before production use, consider adding:

- persistent claim database
- authentication
- authorization
- audit logs
- encrypted document storage
- background jobs
- asynchronous claim processing
- claim status polling
- remote Qdrant
- reviewer persistence
- reviewer override history
- PII protection
- policy versioning
- insurer-specific business rules
- regulatory and compliance review

---

# Current Limitations

ClaimPilot currently does not include:

- persistent claim history
- full authentication
- production insurer integrations
- automatic payment execution
- final legal claim approval
- production-grade fraud scoring
- full reviewer audit persistence

The AI result should therefore be treated as:

```text
preliminary claims intelligence
```

rather than an irreversible final insurance decision.

---

# Roadmap

## Phase 1 — Core Claims Intelligence

- Claim reconstruction
- Policy analysis
- Evidence analysis
- Missing-information detection
- Adjudication
- Critic verification

## Phase 2 — Multimodal Intelligence

- OCR
- Scanned-document support
- Vision analysis
- Damage-photo reasoning
- Cross-modal reasoning
- Settlement calculation

## Phase 2.1 — Grounding and Consistency

- Document source-of-truth grounding
- Visual semantics
- Labour/service-cost handling
- Semantic deduplication
- Readiness-aware settlement
- Critic consistency checks
- Provider hardening

## Phase 3 — Human-in-the-Loop Product

Implemented / in progress:

- React dashboard
- Multi-file evidence upload
- Claim review workspace
- Investigation UI

Planned:

- Reviewer actions
- Reviewer notes
- Claim persistence
- Review queue
- Claim history
- Approval / escalation workflow
- Audit trail

---

# Why ClaimPilot

Traditional claims processing requires adjusters to combine information from:

- forms
- reports
- repair estimates
- policies
- photographs

ClaimPilot demonstrates how an agentic AI system can coordinate these sources while preserving human oversight.

The project focuses on:

```text
Multimodal reasoning
+
Evidence grounding
+
Human-in-the-loop decision support
```

Rather than asking one model to make an opaque decision, ClaimPilot separates reconstruction, policy analysis, evidence reasoning, missing-information detection, adjudication and verification into specialized stages.

---

# Disclaimer

ClaimPilot is an engineering and AI research project.

It is not intended to independently make legally binding insurance decisions without appropriate human review, insurer-specific business rules, regulatory checks and production safeguards.

---

# Author

**Vaibhav Mohanty**

ClaimPilot — Autonomous Insurance Claims Intelligence

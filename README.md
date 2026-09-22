# ClaimPilot

ClaimPilot is a GenAI-powered insurance claims assistant that analyzes claim documents, reasons over policy coverage, identifies inconsistencies, and prepares a preliminary claim assessment for human review.

The project is designed as a multi-agent system for insurance workflows, with a focus on motor insurance claims.

It is being built to simulate how an insurance claims team could use Generative AI to reduce manual document review and speed up early-stage claim assessment.

---

## Project Goal

Insurance claims usually involve multiple documents such as:

- Claim forms
- Insurance policies
- Police reports
- Repair estimates
- Invoices
- Emails
- Supporting documents
- Damage photographs

Manually reviewing all of these documents can take time and may lead to missed inconsistencies.

ClaimPilot aims to automate the first layer of claim analysis by using GenAI agents that can:

- Understand claim documents
- Reconstruct what happened
- Retrieve relevant policy clauses
- Reason about coverage
- Detect contradictions
- Identify unsupported claim items
- Flag cases that require human review

The system does not try to replace the human adjuster. Instead, it acts as an AI claims copilot that prepares a structured and explainable assessment.

---

# ClaimPilot v0.2 — Phase 2 Multimodal Claims Intelligence

## Current Workflow

```text
Claim Documents
      |
      v
Claim Reconstruction Agent
      |
      v
Visual Evidence Agent (damage photographs only)
      |
      v
Policy Retrieval using RAG
      |
      v
Policy Reasoning Agent
      |
      v
Evidence Analysis Agent
      |
      v
Cross-Modal Evidence Agent
      |
      v
Missing Information Agent
      |
      v
Adjudication Agent
      |
      v
Critic Agent
      |
      v
Human Review / Further Processing
```

Damage photographs are retained as private graph inputs and sent only to the
Groq vision provider. Document-like images (claim forms, police reports, and
repair estimates) continue through EasyOCR and reconstruction. The public API
returns filenames and structured findings, never local upload paths.

## Environment

Set the existing text-model variables plus an image-capable Groq model before
submitting damage photographs:

```text
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

Vision defaults to `qwen/qwen3.8-27b`. An explicit empty model is rejected;
provider model/authentication/format errors fail without retries. There is no
local model allowlist. Text-only claims do not call the vision provider.

## Run

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app
```

Do not use `--reload` while the local Qdrant database is open.

## Test

Offline tests do not call Groq:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

To run a live multimodal smoke test, supply a real JPG, JPEG, PNG, or WEBP
damage photograph and explicitly enable it:

```powershell
$env:RUN_LIVE_MULTIMODAL_TESTS = "1"
$env:LIVE_MULTIMODAL_IMAGE_PATH = "C:\path\to\claim_damage.jpg"
.\venv\Scripts\python.exe -m unittest tests.test_live_multimodal -v
```

The live test consumes Groq API quota and is skipped by default.

## v0.2.1 — Phase 2 Hardening

Status: **COMPLETE**. See the [hardening report](docs/phase2-hardening.md) for
the file inventory, A–Z coverage, test results, and remaining limitations.

The existing LangGraph workflow is preserved. Images are classified as
`document_image`, `damage_photo`, or `unknown_image` using pixel layout and
OCR gated by document-like layout. Filenames can only reinforce content
evidence. Unknown images enter visual inspection with uncertainty and a human
review requirement; they are not silently treated as documents or damage.

Vision responses are validated before use. Invalid, empty, incomplete, or
unattributable findings yield neutral evidence requiring review. A maximum of
three photographs per claim is enforced before provider calls, matching the
[Groq vision limit](https://console.groq.com/docs/vision). Each unique photograph
is analyzed separately; `image_observations` retains provenance, and
`duplicate_images` records identical file content without increasing confidence.
Conflicting reliable observations remain visible for human review.

Deterministic guards require confidence of at least 0.8 and adequate quality
before treating an intact region as visually unsupported. Unseen, uncertain,
or blurred regions are unverifiable. Settlement uses decimal arithmetic,
rounds once to cents (half up), clamps payable to zero, and returns null for
invalid/missing inputs. The LLM's payable number is always replaced.

Text and vision calls use three total attempts by default, a 60-second timeout
per attempt, and exponential waits of 1 then 2 seconds. SDK retries are disabled.
429, connection/timeouts, and selected transient server failures retry;
authentication, missing-model, and invalid-format failures do not. Structured
JSON logs on stderr contain stage, claim ID when available, duration, retry
count, model, image count, and extraction method. Request documents, image
payloads, credentials, and local paths are excluded.

The API sanitizes nested results and errors, and page metadata omits extracted
document text and temporary paths. Uploaded files keep the existing local
storage behavior; no new infrastructure is required.

Default discovery blocks Groq calls even if `.env` enables live tests. Live
testing requires both the environment flag and the explicit
`tests.test_live_multimodal` invocation shown above. The older `app/test_*.py`
files are manual scripts, not the offline suite; pytest discovery is restricted
to `tests/`.

Known limits: image routing remains heuristic (unusual scans can remain unknown);
visual confidence is model-reported, not calibrated; duplicate detection uses
exact file bytes; separate image calls use more requests than a joint call.
Real OCR tests require the existing EasyOCR model cache; upstream PyTorch and
Starlette may emit deprecation warnings. A live smoke test validates one
configured image, not all possible images or a full live text/RAG claim.

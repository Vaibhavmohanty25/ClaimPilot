# ClaimPilot v0.2.1 — Phase 2 Hardening

Status: COMPLETE. Verified 2026-09-22.

The existing LangGraph workflow and Phase 1 text-processing path are preserved.
This pass adds reliability guards only; it adds no Phase 3 features or infrastructure.
Pre-existing uncommitted Phase 2 work, `.env`, and tracked bytecode were preserved.

## Verification results

| Check | Result |
| --- | --- |
| Full offline suite | 57 discovered: 56 passed, 1 live test skipped; 30.554 seconds |
| Added tests | 37: 36 hardening tests plus 1 real document-image OCR regression |
| Phase 1 / no-image regression | Passed, including real reconstruction/evidence/missing-info/adjudication/Critic agents with mocked provider responses and a mocked policy agent |
| Existing Phase 2 scenarios | Passed; routing fixtures now assert filename uncertainty and semantic fixtures include explicit confidence/schema |
| Real document-image and scanned-PDF OCR | Passed using existing local EasyOCR models |
| Opt-in live vision | Passed: 1 test, qwen/qwen3.8-27b, configured image; 3.026 seconds; no retries |
| Offline Groq calls | Blocked by test guard; no live Groq requests in final default suite |
| Diff whitespace check | Passed |
| Independent code review | Three issues identified, reproduced, fixed, and verified; follow-up found no further important issues |

The initial baseline discovery unexpectedly attempted the live test because the
existing environment enabled it; the sandbox blocked that connection. Default
discovery now skips live testing even with that flag enabled. Two separately
authorized live smoke runs passed during hardening. The last run exercised the
final vision parser/provider; the subsequent cross-modal-only guard change was
covered by the final offline suite.

## Files added in this pass

- `.env.example`
- `pytest.ini`
- `app/services/observability.py`
- `app/services/provider_retry.py`
- `app/services/privacy.py`
- `tests/offline_support.py`
- `tests/test_00_offline.py`
- `tests/test_hardening.py`
- `docs/phase2-hardening.md`

## Existing files modified in this pass

Some of these were already untracked Phase 2 files when this pass started.

- `README.md`
- `app/main.py`
- `app/graph/claims_graph.py`
- `app/multimodal/file_classifier.py`
- `app/agents/adjudication_agent.py`
- `app/agents/critic_agent.py`
- `app/agents/policy_agent.py`
- `app/agents/vision_agent.py`
- `app/agents/multimodal_evidence_agent.py`
- `app/services/llm.py`
- `app/services/vision_llm.py`
- `app/services/settlement_calculator.py`
- `app/services/evidence_semantics.py`
- `app/services/ocr_service.py`
- `app/services/document_loader.py`
- `tests/__init__.py`
- `tests/test_live_multimodal.py`
- `tests/test_file_routing.py`
- `tests/test_phase2_scenarios.py`
- `tests/test_phase2_document_regression.py`

## Bugs found and hardening changes

1. Filenames determined image type, including unreadable placeholder bytes.
   Routing now uses pixel layout, text density through gated OCR, and a weak
   filename reinforcement. Ambiguous images remain `unknown_image` and require
   review. Document images use `document_image`; explicit OCR loading avoids a
   repeated routing probe.
2. Vision JSON was unvalidated and provider failures could escape the agent.
   Required fields, types, finite confidence, damage entries, and exact image
   references are validated. Fences are accepted, extra fields discarded, and
   unreliable responses produce neutral findings with review required.
3. Visibility guards lacked quality/confidence constraints and could retain
   unsupported contradictory statuses. Deterministic guards now require reliable
   per-image evidence (confidence at least 0.8) for support or intact findings.
   Blurred/unseen evidence becomes unverifiable. Review requirements propagate to
   adjudication; the Critic detects ignored review requirements and unsupported
   approvals.
4. Arithmetic accepted nonfinite values, used binary floating point, and treated
   a missing supported-items list as an empty total. Decimal arithmetic validates
   inputs, rounds once to cents, clamps payable to zero, and returns `None` when
   untrustworthy. LLM payable numbers are always replaced.
5. Provider retries covered only rate limits and compounded SDK retries.
   A shared helper bounds total attempts (default three, maximum five), disables
   SDK retries, uses a 60-second attempt timeout and exponential waits (1, 2,
   then up to 8 seconds), and sanitizes errors. Permanent request/auth/model
   failures do not retry. The obsolete allowlist and active deprecated-model
   README reference were removed.
6. Multiple images lacked reliable attribution and conflict aggregation.
   Unique files are analyzed independently. Exact duplicate files and duplicate
   findings do not increase confidence. Per-image observations retain source
   attribution. Strong evidence survives weak/blurred views, while conflicting
   reliable damaged/intact observations remain reviewable. At most three photos
   are accepted per claim, consistent with the current
   [Groq vision limit](https://console.groq.com/docs/vision).
7. API exception strings and nested outputs could expose paths; page metadata
   included document text; duplicate upload names could overwrite one another.
   Public responses recursively sanitize paths/credentials and omit raw model
   responses. Page metadata is allowlisted. Storage names are unique and source
   filenames remain distinguishable.
8. Debug logging printed policy text and exceptions. Allowlisted JSON stage
   events now report available claim IDs, duration, model, retries, image count,
   extraction method, and outcome without request contents.
9. Live tests could run during default discovery. Offline discovery installs a
   Groq quota guard; live testing requires a separate explicit module invocation.
   Pytest discovery excludes legacy manual `app/test_*.py` scripts.

## Requested A–Z coverage

| Cases | Test coverage |
| --- | --- |
| A, B, Z: Phase 1, no images, no automatic downgrade | `OfflineGraphRegressionTests`, `test_phase2_scenarios`, `test_multimodal_evidence_agent` |
| C, D: document image and scanned PDF OCR | `test_phase2_document_regression` (real OCR fixtures) |
| E, F: damage image, visible damage | `VisionHardeningTests`, strong-alignment scenario |
| G, H, I: intact, unseen, poor quality | `SemanticHardeningTests`, `AdditionalSemanticTests`, Phase 2 scenarios |
| J, K: malformed/empty vision | `VisionHardeningTests`, malformed-vision graph regression |
| L, M: unsupported extension/missing image | `VisionHardeningTests.test_missing_and_unsupported_images_fail_clearly` |
| N, O, P: multiple/duplicate/conflicting images | `VisionHardeningTests`, `AdditionalSemanticTests`, duplicate-upload privacy test |
| Q, R, S: zero/excess deductible, missing supported total | `SettlementHardeningTests`, existing settlement/adjudication tests |
| T, U, V: vision/text 429 and permanent failures | `ProviderHardeningTests` (both provider boundaries, plus bounded timeout backoff) |
| W: API privacy | `PrivacyHardeningTests`, existing API tests, actual HTTP limit test |
| X: adversarial Critic | Existing unsupported-rear-bumper scenario plus ignored-review test |
| Y: clean alignment | `test_strong_multimodal_alignment_is_preserved` |

## Exact commands

Run from the repository root using the existing environment:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app
```

Offline tests and whitespace verification:

```powershell
.\venv\Scripts\python.exe -B -m unittest discover -s tests -v
git -c core.safecrlf=false diff --check
```

Opt-in live vision test, using the already configured
`LIVE_MULTIMODAL_IMAGE_PATH` from the environment or `.env`:

```powershell
$env:RUN_LIVE_MULTIMODAL_TESTS = "1"
$env:GROQ_VISION_MODEL = "qwen/qwen3.8-27b"
.\venv\Scripts\python.exe -B -m unittest tests.test_live_multimodal -v
$env:RUN_LIVE_MULTIMODAL_TESTS = "0"
```

Do not use Uvicorn `--reload` while the local Qdrant database is open.

## Remaining limitations

- Routing is heuristic; unusual scans, screenshots, or sparse documents can
  remain unknown and require review. Photo-like pixels do not prove a vehicle
  is present; the vision agent must establish that.
- Confidence is model-reported, not statistically calibrated. Guards use a
  conservative threshold and the existing limited region vocabulary.
- Duplicate-file detection uses exact bytes, not perceptual similarity. Confidence
  aggregation uses a maximum, never a count-based boost.
- Separate photo analysis uses up to three provider requests per claim and
  preserves conflicts for human reconciliation rather than resolving them.
- Real OCR tests require the existing local EasyOCR model cache. PyTorch/EasyOCR
  and Starlette emit upstream deprecation/CPU warnings in this environment.
- The live smoke verifies one configured image. A full live text/RAG workflow
  was not rerun; offline graph regression mocks external reasoning/retrieval.
- Existing local upload retention and policy-store initialization remain in
  place. Privacy sanitization may over-redact prose containing path-like text.

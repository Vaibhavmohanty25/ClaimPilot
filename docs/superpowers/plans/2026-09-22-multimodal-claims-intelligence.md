# ClaimPilot Multimodal Claims Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2B–2F visual and cross-modal claims intelligence while preserving Phase 1 behavior.

**Architecture:** Route damage photographs away from OCR into a Groq-only vision service, derive structured visual findings, and compare them with reconstruction and repair items in a separate cross-modal agent. Feed the resulting analysis into the existing adjudicator and critic; use deterministic arithmetic only after evidence selection.

**Tech Stack:** Python, FastAPI, LangGraph, Groq SDK, Pillow, EasyOCR, PyMuPDF, standard-library unittest.

**Spec:** `docs/superpowers/specs/2026-09-22-multimodal-claims-intelligence-design.md`

## Global Constraints

- Preserve text-only Phase 1 graph behavior and the existing shared local Qdrant client.
- Use Groq only; add no OpenAI, Claude, CV-model, queue, or worker dependencies.
- Do not OCR damage photographs; do not expose upload paths in API output.
- Keep normal tests offline and API-quota-free; gate live vision tests behind an environment variable.
- Treat `not visible` as unverifiable, never as intact or undamaged.

---

### Task 1: Deterministic helpers and input routing

**Files:**
- Create: `app/services/settlement_calculator.py`
- Modify: `app/multimodal/file_classifier.py`, `app/services/document_loader.py`
- Test: `tests/test_settlement_calculator.py`, `tests/test_file_routing.py`

**Interfaces:**
- Produces `calculate_payable_amount(supported_amounts: list[object], deductible: object) -> int | None`.
- Produces `classify_image_content(path: str) -> str` returning `damage_photo` or `image_document`.

- [ ] Write failing tests for reliable arithmetic, unknown amounts, and damage-photo routing.
- [ ] Run `python -m unittest tests.test_settlement_calculator tests.test_file_routing -v` and observe failures.
- [ ] Implement minimal helpers and rerun the same command until green.

### Task 2: Groq vision provider and visual agent

**Files:**
- Create: `app/services/vision_llm.py`
- Modify: `app/agents/vision_agent.py`, `app/prompts/visual_evidence.txt`
- Test: `tests/test_vision_agent.py`

**Interfaces:**
- Produces `generate_vision_json(prompt: str, image_paths: list[str]) -> str` with capability validation.
- Produces `analyze_visual_evidence(image_files: list[dict]) -> dict` and a neutral no-image schema.

- [ ] Write failing tests for neutral no-image output and parsing fallback.
- [ ] Run `python -m unittest tests.test_vision_agent -v` and observe failures.
- [ ] Implement provider and agent, then rerun the test command until green.

### Task 3: Cross-modal analysis

**Files:**
- Create: `app/agents/multimodal_evidence_agent.py`, `app/prompts/multimodal_evidence.txt`
- Test: `tests/test_multimodal_evidence_agent.py`

**Interfaces:**
- Produces `analyze_cross_modal_evidence(claim_reconstruction, evidence_analysis, visual_analysis) -> dict`.

- [ ] Write failing tests for no-image insufficiency and JSON fallback.
- [ ] Run `python -m unittest tests.test_multimodal_evidence_agent -v` and observe failures.
- [ ] Implement prompt-fed semantic comparison and rerun the test command until green.

### Task 4: Graph, adjudication, critic, and API integration

**Files:**
- Modify: `app/graph/claims_graph.py`, `app/agents/adjudication_agent.py`, `app/agents/critic_agent.py`, `app/prompts/adjudication.txt`, `app/prompts/critic.txt`, `app/main.py`
- Test: `tests/test_claim_graph_multimodal.py`, `tests/test_api_multimodal.py`

**Interfaces:**
- Graph accepts `document_metadata` and private `image_files` and returns `visual_analysis` and `cross_modal_analysis`.
- API returns public metadata, visual analysis, and cross-modal analysis without private paths.

- [ ] Write failing graph/API tests for no-photo compatibility and withheld path fields.
- [ ] Run the targeted unittest modules and observe failures.
- [ ] Integrate nodes, agent inputs, response fields, and deterministic payable override, then rerun until green.

### Task 5: Regression and opt-in live validation

**Files:**
- Create: `tests/test_phase2_scenarios.py`, `tests/test_live_multimodal.py`
- Modify: `README.md`, `requirements.txt`

- [ ] Write deterministic scenario tests for strong alignment, intact rear-bumper contradiction, region-not-visible treatment, and adversarial critic inputs.
- [ ] Run `python -m unittest discover -s tests -v` and observe failures before completing each behavior.
- [ ] Add run/test documentation and the live-test environment gate.
- [ ] Run the full offline suite and report exact output; run live tests only when explicitly enabled and credentials/model are configured.

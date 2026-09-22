# Multimodal Claims Intelligence Design

## Goal

Extend ClaimPilot's existing Phase 1 and Phase 2A claim pipeline with visual damage analysis and cross-modal verification, without changing policy RAG or breaking text-only claims.

## Architecture

Uploaded files are classified before extraction. Text files and PDFs remain on the existing document path. Images identified as document-like are OCRed and their text enters reconstruction; images identified as damage photographs are retained only as private graph inputs for a Groq vision provider. The Visual Evidence Agent produces factual visual observations, while the Cross-Modal Evidence Agent compares those observations with reconstructed documents and repair items.

The LangGraph flow becomes `reconstruct_claim -> visual_analysis -> policy_reasoning -> evidence_analysis -> cross_modal_evidence -> missing_information -> adjudication -> critic`. The visual node returns a neutral schema when no photographs are supplied. Policy reasoning remains exclusively based on reconstruction and retrieved policy context.

## Safety and Semantics

Visual findings distinguish a region that is not visible from a region that is visible and appears intact. Cross-modal conclusions call an item `unverifiable` when no image depicts its region, and only call it visually unsupported when the region is clearly visible and intact or visual evidence materially contradicts it. Image paths are graph-private and never returned by the API.

## Settlement

The LLM selects supported priced repair items. A deterministic helper then sums known selected amounts and subtracts a known deductible; it returns `None` if a reliable calculation is impossible. The helper does not make coverage or evidence decisions.

## Testing

Standard-library `unittest` tests cover deterministic services, routing, graph behavior with injected agent functions, and FastAPI integration with mocked graph output. Live Groq vision tests are opt-in and gated by `RUN_LIVE_MULTIMODAL_TESTS=1` plus a multimodal model configuration.

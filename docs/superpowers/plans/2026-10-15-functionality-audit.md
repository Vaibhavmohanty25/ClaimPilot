# ClaimPilot functionality audit and repair plan

**Goal:** Verify every implemented README capability, repair reproducible defects, and distinguish offline evidence from live-service checks.

**Scope:** Existing PDF/text/image intake, OCR, RAG, eight-stage graph, settlement, critic, dashboard/upload/review, provider handling, deployment instructions. Roadmap features remain out of scope.

- [x] Download clean repository and map README capabilities to code/tests.
- [x] Establish dependency environment and baseline offline test results.
- [x] Reproduce and repair PDF/RAG defects with regression tests.
- [x] Reproduce and repair graph grounding, critic, and settlement defects.
- [x] Verify HTTP intake, errors, concurrency, CORS and provider handling.
- [x] Build frontend and exercise upload/review states.
- [x] Re-run combined checks, inspect diff, and produce a feature-by-feature report and portable patch.

External limits must be explicit: no Groq credentials are available; generated model responses cannot establish live model quality. Real OCR and vector retrieval require model weights and dependencies.

## Deployment follow-up

Render deployment and requests every 15 minutes are requested. Render/Vercel connections and runtime Groq secret are required. Docker/Blueprint preparation is complete and schema-validated; actual Docker build and live verification remain pending. No URL-specific keep-alive is active before deployment.

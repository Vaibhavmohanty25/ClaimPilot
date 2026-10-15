# ClaimPilot deployment

Deploy the React frontend and FastAPI backend as separate services. The repository root is the backend build context; `frontend/` is the Vercel project root.

## Vercel frontend

1. Import the GitHub repository into Vercel.
2. Set **Root Directory** to `frontend` and **Framework Preset** to `Vite`.
3. Set **Install Command** to `npm ci`, **Build Command** to `npm run build`, and **Output Directory** to `dist`.
4. Add `VITE_API_BASE_URL=https://BACKEND_URL`, replacing the placeholder with the backend's public HTTPS origin and omitting a trailing slash.
5. Deploy. `frontend/vercel.json` rewrites React Router paths to `index.html`.

Production builds now reject a missing, HTTP, or loopback `VITE_API_BASE_URL`. Use the actual public HTTPS backend URL; a Vercel frontend cannot reach a backend on the visitor's `127.0.0.1`. `VITE_API_BASE_URL` is embedded during the frontend build. Redeploy the frontend after changing it. Local development retains the existing `http://127.0.0.1:8000` fallback.

## Container backend

Use the repository root as the container build context on a host such as Render, Railway, or Fly.io. The root `Dockerfile` installs `requirements.txt`, copies `app/` and `data/`, and starts Uvicorn on the host-provided `PORT` (default `8000`). Allocate enough memory and disk for PyTorch, EasyOCR, SentenceTransformers, and model downloads.

For a host using native Python build and start settings instead of the Dockerfile:

```text
Build: pip install -r requirements.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Run from the repository root with a writable working directory. Configure these backend variables in the host's secret/settings UI:

```text
GROQ_API_KEY=<secret>
GROQ_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.8-27b
FRONTEND_ORIGIN=https://YOUR-VERCEL-DOMAIN
```

The optional live text retry settings are `CLAIMPILOT_TEXT_MAX_ATTEMPTS=4` and `CLAIMPILOT_TEXT_429_BACKOFF=10,20,35`. Their existing defaults apply when unset. Set `FRONTEND_ORIGIN` to the exact Vercel origin, without a trailing slash. Local Vite origins remain allowed. Keep production values out of committed `.env` files.

## Qdrant storage and policy data

The backend uses `QdrantClient(path=".qdrant")`, one `motor_policy` collection and one active policy. Ingesting another policy replaces the active policy; insurer/policy selection is not implemented. `QDRANT_URL` and `QDRANT_API_KEY` are not read.

The Docker build caches public embedding/OCR models and seeds `data/policies/motor_policy.txt` into the image in separate preparation processes. This needs build-time internet, but no Groq key. Fresh containers recover this bundled baseline even on ephemeral storage. Runtime Hugging Face access is offline.

For native Python hosting, or a volume mounted over `.qdrant` (which hides the seeded image directory), initialize that storage before starting the backend:

```text
python -m app.rag.ingest
```

Stop the backend before ingestion: embedded Qdrant permits only one process to open its storage. Retain volumes across deployments and use a single backend instance. Remote Qdrant requires a code change. Uploaded files in `uploads/` disappear on ephemeral-host restarts; claim persistence remains a roadmap feature.

## Render deployment

`render.yaml` defines the Docker service `claimpilot-api`: free plan, manual deploys, `/` health check, `FRONTEND_ORIGIN=https://claimpilot-five.vercel.app`, and a prompt for runtime secret `GROQ_API_KEY`. Never put the key in Git or Docker build arguments.

Create a Render Blueprint from the branch containing these changes. Provide the Groq key, deploy, and verify the root response and a synthetic scanned PDF claim. Set Vercel's `VITE_API_BASE_URL` to the resulting public HTTPS service URL, then rebuild the frontend.

Free Render web services have 512 MB RAM. Full PyTorch/EasyOCR/SentenceTransformer processing can exceed that limit; health-check success alone does not prove scanned claims work. Use measured memory and a scanned-PDF test to select a suitable plan. A paid plan requires an approved budget.

Free services sleep after 15 minutes without inbound traffic. Requests every 15 minutes match the requested cadence but can arrive after the idle boundary, so they cannot guarantee uninterrupted availability. Checks should send a cheap `GET /` to the verified backend URL. A successful deployment and its URL are required before activating a URL-specific schedule.

References: [free limits](https://render.com/docs/free), [compute plans](https://render.com/docs/compute-plans), [Blueprint specification](https://render.com/docs/blueprint-spec).

## Connect both services

After deploying the backend, copy its public HTTPS URL into Vercel's `VITE_API_BASE_URL`. Set the backend's `FRONTEND_ORIGIN` to the Vercel frontend URL. Redeploy each service after changing its environment variables. Check the backend root endpoint and then submit a claim from the frontend.

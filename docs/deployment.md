# ClaimPilot deployment

Deploy the React frontend and FastAPI backend as separate services. The repository root is the backend build context; `frontend/` is the Vercel project root.

## Vercel frontend

1. Import the GitHub repository into Vercel.
2. Set **Root Directory** to `frontend` and **Framework Preset** to `Vite`.
3. Set **Install Command** to `npm ci`, **Build Command** to `npm run build`, and **Output Directory** to `dist`.
4. Add `VITE_API_BASE_URL=https://BACKEND_URL`, replacing the placeholder with the backend's public HTTPS origin and omitting a trailing slash.
5. Deploy. `frontend/vercel.json` rewrites React Router paths to `index.html`.

`VITE_API_BASE_URL` is embedded during the frontend build. Redeploy the frontend after changing it. Local development retains the existing `http://127.0.0.1:8000` fallback.

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

The current backend uses `QdrantClient(path=".qdrant")`. It does not read `QDRANT_URL` or `QDRANT_API_KEY`. A stateless container loses the policy collection, so attach persistent storage at `/app/.qdrant` (or `.qdrant` relative to a native host's working directory). Seed the `motor_policy` collection once, from the repository root, with:

```text
python -m app.rag.ingest
```

Run that command against the same mounted storage used by the running service, retain the volume across deployments, and use a single backend instance with the embedded Qdrant store. A remote Qdrant service requires a separate code change and migration of the policy collection; setting remote Qdrant variables alone has no effect.

The backend writes uploaded claim files to `uploads/`. Choose the host's persistent or temporary storage policy for that directory.

## Connect both services

After deploying the backend, copy its public HTTPS URL into Vercel's `VITE_API_BASE_URL`. Set the backend's `FRONTEND_ORIGIN` to the Vercel frontend URL. Redeploy each service after changing its environment variables. Check the backend root endpoint and then submit a claim from the frontend.

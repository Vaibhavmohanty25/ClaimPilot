import os
import asyncio
import hashlib
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from uuid import uuid4
from time import perf_counter
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from fastapi import FastAPI, File, Header, HTTPException, UploadFile

from app.graph.claims_graph import claim_graph
from app.services.document_loader import load_document
from app.multimodal.file_classifier import classify_file
from app.services.privacy import safe_filename as sanitize_filename, public_response
from app.services.observability import log_event
from app.services.vision_llm import MAX_VISION_IMAGES
from app.services.claim_jobs import ClaimJobQueue, SavedUpload, cleanup_uploads
from app.services.job_progress import report_progress


@asynccontextmanager
async def lifespan(application):
    try:
        yield
    finally:
        queue = getattr(application.state, "claim_jobs", None)
        if queue is not None:
            await queue.shutdown()


app = FastAPI(
    lifespan=lifespan,
    title="ClaimPilot",
    description=(
        "Agentic GenAI platform for insurance claim assessment "
        "with multimodal document intelligence."
    ),
    version="0.2.1",
)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip().rstrip("/")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if frontend_origin:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PyMuPDF and first-use OCR initialization must never overlap. A dedicated
# worker keeps extraction off the event loop and on one thread across claims.
_document_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="claimpilot-documents")


async def _run_document_operation(operation, *args):
    return await _finish_background(asyncio.get_running_loop().run_in_executor(
        _document_executor, partial(operation, *args)
    ))


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


@app.get("/")
def root():
    return {
        "project": "ClaimPilot",
        "status": "running",
        "phase": "2",
    }


async def _process_saved_files(files, *, optimized=False):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files were uploaded.",
        )

    claim_id = (
        f"CLM-{uuid4().hex[:8].upper()}"
    )

    document_sections = []
    processed_files = []
    document_metadata = []
    image_files = []
    private_paths = []
    used_filenames = set()

    for uploaded_file in files:
        if not uploaded_file.filename:
            continue

        try:
            safe_filename = sanitize_filename(uploaded_file.filename)
            original_filename = safe_filename
            suffix = 2
            while safe_filename.casefold() in used_filenames:
                safe_filename = f"{suffix}-{original_filename}"
                suffix += 1
            used_filenames.add(safe_filename.casefold())
            file_path = uploaded_file.path
            private_paths.extend([str(file_path), str(file_path.resolve()), file_path.name])
            report_progress("extracting", f"Reading document {len(processed_files) + 1} of {len(files)}.")

            start = perf_counter()
            classification = await _run_document_operation(classify_file, str(file_path))

            if classification["content_type"] in ("damage_photo", "unknown_image"):
                image_files.append(
                    {
                        "filename": safe_filename,
                        "path": str(file_path),
                        "classification": classification["content_type"],
                    }
                )
                processed_files.append(safe_filename)
                document_metadata.append(
                    {
                        "filename": safe_filename,
                        "file_type": "image",
                        "content_type": classification["content_type"],
                        "classification_confidence": classification.get("classification_confidence", 0),
                        "extraction_method": "vision_pending",
                        "pages": 1,
                    }
                )
                log_event("image_routing", True, claim_id=claim_id, extraction_method="vision_pending",
                          image_count=1, duration_ms=round((perf_counter() - start) * 1000, 2))
                continue

            # --------------------------------------------------
            # Phase 2A document intelligence
            # --------------------------------------------------

            document_result = await _run_document_operation(
                load_document, str(file_path)
            )

            extracted_text = (
                document_result.get(
                    "text",
                    "",
                )
            )

            if not extracted_text.strip():
                raise ValueError(
                    "No readable text could be extracted."
                )

            # --------------------------------------------------
            # Preserve extracted text for Phase 1 reasoning graph
            # --------------------------------------------------

            document_sections.append(
                f"""
==================================================
DOCUMENT: {safe_filename}
FILE TYPE: {document_result.get("file_type")}
CONTENT TYPE: {document_result.get("content_type")}
EXTRACTION METHOD: {document_result.get("extraction_method")}
==================================================

{extracted_text}
"""
            )

            processed_files.append(
                safe_filename
            )

            # --------------------------------------------------
            # Preserve multimodal metadata for Phase 2
            # --------------------------------------------------

            metadata = {
                "filename": safe_filename,
                "file_type": document_result.get(
                    "file_type"
                ),
                "content_type": document_result.get(
                    "content_type"
                ),
                "extraction_method": document_result.get(
                    "extraction_method"
                ),
                "pages": document_result.get(
                    "pages"
                ),
            }

            if (
                document_result.get(
                    "file_type"
                )
                == "image"
            ):
                metadata[
                    "image_width"
                ] = document_result.get(
                    "image_width"
                )

                metadata[
                    "image_height"
                ] = document_result.get(
                    "image_height"
                )

            if document_result.get(
                "page_details"
            ):
                metadata["page_details"] = [
                    {key: page.get(key) for key in ("page_number", "extraction_method")}
                    for page in document_result["page_details"]
                ]

            document_metadata.append(
                metadata
            )
            log_event("document_extraction", True, claim_id=claim_id, extraction_method=metadata["extraction_method"],
                      duration_ms=round((perf_counter() - start) * 1000, 2))

        except ValueError:
            log_event("document_extraction", False, claim_id=claim_id, error_code="unsupported_or_unreadable_file")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported or unreadable file "
                    f"'{safe_filename}'."
                ),
            )

        except Exception:
            log_event("document_extraction", False, claim_id=claim_id, error_code="document_processing_failed")

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to process "
                    f"'{safe_filename}'."
                ),
            )


    if not document_sections and not image_files:
        raise HTTPException(
            status_code=400,
            detail=(
                "No valid claim documents "
                "were processed."
            ),
        )

    raw_documents = "\n".join(document_sections)
    if not raw_documents:
        raw_documents = (
            "No textual claim documents were supplied. "
            "Do not infer incident facts from this placeholder."
        )

    if len(image_files) > MAX_VISION_IMAGES:
        raise HTTPException(status_code=400, detail="Vision limit exceeded: at most 3 images per claim.")

    # ------------------------------------------------------
    # Existing Phase 1 LangGraph pipeline
    # ------------------------------------------------------

    try:
        result = await _finish_background(asyncio.ensure_future(run_in_threadpool(
            _queued_graph_invoke if optimized else claim_graph.invoke,
            {
                "claim_id": claim_id,
                "raw_documents": raw_documents,
                "document_metadata": document_metadata,
                "image_files": image_files,
            }
        )))

    except Exception:
        log_event("claim_processing", False, claim_id=claim_id, error_code="claim_processing_failed")

        raise HTTPException(
            status_code=500,
            detail="Claim processing failed. Review server stage logs and provider configuration.",
        )

    # ------------------------------------------------------
    # Final response
    # ------------------------------------------------------

    return public_response({
        "claim_id": claim_id,
        "status": "critic_verification_complete",
        "phase": "2",

        "files_processed": processed_files,

        # New Phase 2A metadata
        "document_metadata": (
            document_metadata
        ),

        # Existing Phase 1 outputs
        "reconstruction": result.get(
            "claim_reconstruction"
        ),

        "visual_analysis": result.get(
            "visual_analysis"
        ),

        "coverage_analysis": result.get(
            "coverage_analysis"
        ),

        "policy_context": result.get(
            "policy_context"
        ),

        "evidence_analysis": result.get(
            "evidence_analysis"
        ),

        "cross_modal_analysis": result.get(
            "cross_modal_analysis"
        ),

        "missing_information": result.get(
            "missing_information"
        ),

        "adjudication": result.get(
            "adjudication"
        ),

        "critic_feedback": result.get(
            "critic_feedback"
        ),
    }, private_paths)


MAX_FILES = 10
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}


async def _finish_background(awaitable):
    # Cancellation must not delete uploads or release the provider lock while
    # a document/provider thread still uses them.
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        finally:
            raise


def _queued_graph_invoke(state):
    from app.graph.claims_graph import optimized_claim_graph
    return optimized_claim_graph.invoke(state)


def _get_job_queue():
    loop = asyncio.get_running_loop()
    queue = getattr(app.state, "claim_jobs", None)
    if queue is None or getattr(app.state, "claim_jobs_loop", None) is not loop:
        async def process(files):
            return await _process_saved_files(files, optimized=True)
        queue = ClaimJobQueue(process)
        app.state.claim_jobs = queue
        app.state.claim_jobs_loop = loop
    return queue


async def _persist_uploads(files, *, validate_types=True):
    saved = []
    digest = hashlib.sha256()
    total = 0
    used_names = set()
    try:
        if not files or len(files) > MAX_FILES:
            raise HTTPException(400, f"Upload between 1 and {MAX_FILES} files per claim.")
        for upload in files:
            if not upload.filename:
                raise HTTPException(400, "Every uploaded file needs a filename.")
            name = sanitize_filename(upload.filename)
            if validate_types and Path(name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
                raise HTTPException(400, "Unsupported file type. Upload PDF, text, or image documents.")
            original = name
            number = 2
            while name.casefold() in used_names:
                name = f"{number}-{original}"
                number += 1
            used_names.add(name.casefold())
            path = UPLOAD_DIR / f"{uuid4().hex}_{name}"
            saved.append(SavedUpload(name, path))
            file_digest = hashlib.sha256()
            length = 0
            with path.open("wb") as target:
                while True:
                    # Tiny legacy in-process callers may implement read() only.
                    read_once = False
                    try:
                        chunk = await upload.read(1024 * 1024)
                    except TypeError:
                        chunk = await upload.read()
                        read_once = True
                    if not chunk:
                        break
                    length += len(chunk)
                    total += len(chunk)
                    if length > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                        raise HTTPException(413, "Upload limit exceeded: 20 MiB per file and 40 MiB per claim.")
                    target.write(chunk)
                    file_digest.update(chunk)
                    if read_once:
                        break
            if not length:
                raise HTTPException(400, "Uploaded files must not be empty.")
            # Structured boundaries avoid ambiguity and include names/order as
            # they affect graph document boundaries and public result metadata.
            encoded_name = name.encode("utf-8")
            digest.update(len(encoded_name).to_bytes(4, "big"))
            digest.update(encoded_name)
            digest.update(length.to_bytes(8, "big"))
            digest.update(file_digest.digest())
        return saved, digest.hexdigest()
    except BaseException:
        cleanup_uploads(saved)
        raise
    finally:
        for upload in files:
            await upload.close()


@app.post("/claims/process")
async def process_claim(files: list[UploadFile] = File(...)):
    saved, _ = await _persist_uploads(files, validate_types=False)
    try:
        async with _get_job_queue().processing_lock:
            return await _process_saved_files(saved)
    except BaseException:
        cleanup_uploads(saved)
        raise


@app.post("/claims/jobs", status_code=202)
async def create_claim_job(files: list[UploadFile] = File(...),
                           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key is not None and (not idempotency_key.strip() or len(idempotency_key) > 200):
        for upload in files:
            await upload.close()
        raise HTTPException(400, "Idempotency-Key must contain between 1 and 200 characters.")
    saved, fingerprint = await _persist_uploads(files)
    return await _get_job_queue().submit(saved, fingerprint, idempotency_key)


@app.get("/claims/jobs/{job_id}")
async def get_claim_job(job_id: str):
    return _get_job_queue().get(job_id)

from pathlib import Path
from uuid import uuid4
from time import perf_counter
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.graph.claims_graph import claim_graph
from app.services.document_loader import load_document
from app.multimodal.file_classifier import classify_file
from app.services.privacy import safe_filename as sanitize_filename, public_response
from app.services.observability import log_event
from app.services.vision_llm import MAX_VISION_IMAGES


app = FastAPI(
    title="ClaimPilot",
    description=(
        "Agentic GenAI platform for insurance claim assessment "
        "with multimodal document intelligence."
    ),
    version="0.2.1",
)
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


@app.post("/claims/process")
async def process_claim(
    files: list[UploadFile] = File(...)
):
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
            await uploaded_file.close()
            continue

        try:
            safe_filename = sanitize_filename(uploaded_file.filename)
            original_filename = safe_filename
            suffix = 2
            while safe_filename.casefold() in used_filenames:
                safe_filename = f"{suffix}-{original_filename}"
                suffix += 1
            used_filenames.add(safe_filename.casefold())
            file_path = (
                UPLOAD_DIR
                / f"{claim_id}_{uuid4().hex[:8]}_{safe_filename}"
            )
            private_paths.extend([str(file_path), str(file_path.resolve()), file_path.name])

            file_bytes = await uploaded_file.read()

            file_path.write_bytes(
                file_bytes
            )

            start = perf_counter()
            classification = classify_file(str(file_path))

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

            document_result = load_document(
                str(file_path)
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

        finally:
            await uploaded_file.close()

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
        result = claim_graph.invoke(
            {
                "claim_id": claim_id,
                "raw_documents": raw_documents,
                "document_metadata": document_metadata,
                "image_files": image_files,
            }
        )

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

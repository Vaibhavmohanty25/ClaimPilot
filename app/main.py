from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.graph.claims_graph import claim_graph
from app.services.document_loader import load_document


app = FastAPI(
    title="ClaimPilot",
    description=(
        "Agentic GenAI platform for insurance claim assessment "
        "with multimodal document intelligence."
    ),
    version="0.2.0",
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
        "phase": "2A",
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

    for uploaded_file in files:
        if not uploaded_file.filename:
            continue

        try:
            file_path = (
                UPLOAD_DIR
                / f"{claim_id}_{uploaded_file.filename}"
            )

            file_bytes = await uploaded_file.read()

            file_path.write_bytes(
                file_bytes
            )

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
DOCUMENT: {uploaded_file.filename}
FILE TYPE: {document_result.get("file_type")}
CONTENT TYPE: {document_result.get("content_type")}
EXTRACTION METHOD: {document_result.get("extraction_method")}
==================================================

{extracted_text}
"""
            )

            processed_files.append(
                uploaded_file.filename
            )

            # --------------------------------------------------
            # Preserve multimodal metadata for Phase 2
            # --------------------------------------------------

            metadata = {
                "filename": document_result.get(
                    "filename"
                ),
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
                metadata[
                    "page_details"
                ] = document_result.get(
                    "page_details"
                )

            document_metadata.append(
                metadata
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported or unreadable file "
                    f"'{uploaded_file.filename}': "
                    f"{error}"
                ),
            )

        except Exception as error:
            print(
                "DOCUMENT PROCESSING ERROR:",
                repr(error),
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to process "
                    f"'{uploaded_file.filename}': "
                    f"{error}"
                ),
            )

        finally:
            await uploaded_file.close()

    if not document_sections:
        raise HTTPException(
            status_code=400,
            detail=(
                "No valid claim documents "
                "were processed."
            ),
        )

    raw_documents = "\n".join(
        document_sections
    )

    # ------------------------------------------------------
    # Existing Phase 1 LangGraph pipeline
    # ------------------------------------------------------

    try:
        result = claim_graph.invoke(
            {
                "claim_id": claim_id,
                "raw_documents": raw_documents,
            }
        )

    except Exception as error:
        print(
            "CLAIM PROCESSING ERROR:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    # ------------------------------------------------------
    # Final response
    # ------------------------------------------------------

    return {
        "claim_id": claim_id,
        "status": "critic_verification_complete",
        "phase": "2A",

        "files_processed": processed_files,

        # New Phase 2A metadata
        "document_metadata": (
            document_metadata
        ),

        # Existing Phase 1 outputs
        "reconstruction": result.get(
            "claim_reconstruction"
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

        "missing_information": result.get(
            "missing_information"
        ),

        "adjudication": result.get(
            "adjudication"
        ),

        "critic_feedback": result.get(
            "critic_feedback"
        ),
    }
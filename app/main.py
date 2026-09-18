from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.graph.claims_graph import claim_graph
from app.services.document_loader import load_document


app = FastAPI(
    title="ClaimPilot",
    description="Agentic GenAI platform for insurance claim assessment.",
    version="0.1.0",
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
        "phase": "1F",
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

    claim_id = f"CLM-{uuid4().hex[:8].upper()}"

    document_sections = []
    processed_files = []

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

            extracted_text = load_document(
                str(file_path)
            )

            document_sections.append(
                f"""
==================================================
DOCUMENT: {uploaded_file.filename}
==================================================

{extracted_text}
"""
            )

            processed_files.append(
                uploaded_file.filename
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file "
                    f"'{uploaded_file.filename}': {error}"
                ),
            )

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to process "
                    f"'{uploaded_file.filename}': {error}"
                ),
            )

        finally:
            await uploaded_file.close()

    if not document_sections:
        raise HTTPException(
            status_code=400,
            detail="No valid claim documents were processed.",
        )

    raw_documents = "\n".join(
        document_sections
    )

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

    return {
        "claim_id": claim_id,
        "status": "critic_verification_complete",
        "files_processed": processed_files,

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
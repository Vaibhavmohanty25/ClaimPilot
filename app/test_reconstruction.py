from app.services.document_loader import load_document
from app.agents.claim_reconstruction import reconstruct_claim


files = [
    "data/sample_claim/claim_form.txt",
    "data/sample_claim/police_report.txt",
    "data/sample_claim/repair_estimate.txt",
]


documents = []

for file_path in files:

    text = load_document(
        file_path
    )

    documents.append(
        f"""
============================
DOCUMENT: {file_path}
============================

{text}
"""
    )


combined_documents = "\n".join(
    documents
)


result = reconstruct_claim(
    combined_documents
)


print(result)
from pprint import pprint

from app.services.document_loader import (
    load_document,
)


TEST_FILES = [
    "data/sample_claim/claim_form.txt",
]


for file_path in TEST_FILES:
    print(
        "\n=============================="
    )

    print(
        f"Testing: {file_path}"
    )

    result = load_document(
        file_path
    )

    pprint(
        result
    )
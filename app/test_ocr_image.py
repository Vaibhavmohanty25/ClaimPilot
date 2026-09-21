from pprint import pprint

from app.services.document_loader import load_document


FILE_PATH = "data/ocr_test/police_report.png"


result = load_document(
    FILE_PATH
)


print("\n=== IMAGE OCR TEST ===\n")

pprint(result)
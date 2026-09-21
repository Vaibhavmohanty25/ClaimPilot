from pprint import pprint

from app.services.document_loader import load_document


FILE_PATH = "data/ocr_test/police_report_scan.pdf"

result = load_document(FILE_PATH)

print("\n=== SCANNED PDF OCR TEST ===\n")
pprint(result)
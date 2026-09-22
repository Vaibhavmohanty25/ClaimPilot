import unittest

from app.services.document_loader import load_document


class PhaseTwoDocumentRegressionTests(unittest.TestCase):
    def test_document_image_ocr_keeps_readable_police_report(self):
        result = load_document("data/ocr_test/police_report.png")
        self.assertEqual(result["content_type"], "document_image")
        self.assertEqual(result["extraction_method"], "ocr")
        self.assertIn("POLICE", result["text"].upper())

    def test_scanned_police_report_remains_available_to_document_pipeline(self):
        result = load_document("data/ocr_test/police_report_scan.pdf")

        self.assertEqual(result["file_type"], "pdf")
        self.assertEqual(result["content_type"], "scanned_or_mixed_pdf")
        self.assertEqual(result["extraction_method"], "mixed")
        self.assertIn("POLICE", result["text"].upper())

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from app.services.document_loader import load_pdf


class PdfExtractionTests(unittest.TestCase):
    def make_pdf(self, directory, texts):
        path = Path(directory) / "evidence.pdf"
        with pymupdf.open() as document:
            for text in texts:
                page = document.new_page()
                if text:
                    page.insert_text((72, 72), text)
            document.save(path)
        return path

    def test_blank_pdf_has_no_readable_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_pdf(directory, [""])
            with patch("app.services.document_loader.extract_text_from_image", return_value=""):
                result = load_pdf(str(path))
        self.assertFalse(result["text"].strip())

    def test_short_native_text_survives_empty_ocr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_pdf(directory, ["Claim INR 58000"])
            with patch("app.services.document_loader.extract_text_from_image", return_value=""):
                result = load_pdf(str(path))
        self.assertIn("Claim INR 58000", result["text"])
        self.assertEqual(result["page_details"][0]["extraction_method"], "native_text")

    def test_digital_pdf_preserves_native_text_without_ocr(self):
        text = "POLICE REPORT: Collision at the crossing. Damage to the front bumper."
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_pdf(directory, [text])
            with patch("app.services.document_loader.extract_text_from_image", side_effect=AssertionError("Unexpected OCR")):
                result = load_pdf(str(path))
        self.assertIn(text, result["text"])
        self.assertEqual(result["content_type"], "digital_pdf")
        self.assertEqual(result["pages"], 1)

    def test_mixed_pdf_keeps_page_order_and_removes_rendered_image(self):
        text = "POLICE REPORT: Collision at the crossing. Damage to the front bumper."
        rendered_paths = []
        def recognize(image_path):
            self.assertTrue(Path(image_path).exists())
            rendered_paths.append(image_path)
            return "REPAIR ESTIMATE: Front bumper INR 30000"
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_pdf(directory, [text, ""])
            with patch("app.services.document_loader.extract_text_from_image", side_effect=recognize):
                result = load_pdf(str(path))
        self.assertLess(result["text"].index("POLICE"), result["text"].index("REPAIR"))
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["extraction_method"], "mixed")
        self.assertTrue(rendered_paths)
        self.assertTrue(all(not Path(path).exists() for path in rendered_paths))

    def test_rendered_pdf_image_is_removed_when_ocr_fails(self):
        rendered_paths = []
        def fail_ocr(image_path):
            rendered_paths.append(image_path)
            raise RuntimeError("OCR unavailable")
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_pdf(directory, [""])
            with patch("app.services.document_loader.extract_text_from_image", side_effect=fail_ocr):
                with self.assertRaises(RuntimeError):
                    load_pdf(str(path))
        self.assertTrue(rendered_paths)
        self.assertTrue(all(not Path(path).exists() for path in rendered_paths))

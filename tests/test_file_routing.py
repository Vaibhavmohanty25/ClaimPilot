import tempfile
import unittest
from pathlib import Path

from app.multimodal.file_classifier import classify_file


class FileRoutingTests(unittest.TestCase):
    def test_damage_filename_alone_preserves_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "front_bumper_damage.jpg"
            path.write_bytes(b"placeholder")
            result = classify_file(str(path))

        self.assertEqual(result["file_type"], "image")
        self.assertEqual(result["content_type"], "unknown_image")

    def test_document_filename_alone_preserves_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "garage_repair_estimate.png"
            path.write_bytes(b"placeholder")
            result = classify_file(str(path))

        self.assertEqual(result["content_type"], "unknown_image")

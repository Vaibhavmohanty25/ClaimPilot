import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content

    async def close(self):
        return None


class CapturingGraph:
    def __init__(self):
        self.state = None

    def invoke(self, state):
        self.state = state
        return {
            "claim_reconstruction": {"reported_damage": ["front bumper"]},
            "visual_analysis": {"images_analyzed": ["front_bumper_damage.jpg"]},
            "coverage_analysis": {},
            "policy_context": [],
            "evidence_analysis": {},
            "cross_modal_analysis": {"cross_modal_status": "STRONG_ALIGNMENT"},
            "missing_information": {},
            "adjudication": {},
            "critic_feedback": {},
        }


class ApiMultimodalTests(unittest.TestCase):
    def test_photo_only_claim_reaches_visual_graph_with_neutral_document_text(self):
        graph = CapturingGraph()

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main, "load_document") as loader, patch.object(main, "claim_graph", graph):
                response = asyncio.run(
                    main.process_claim([FakeUpload("front_bumper_damage.jpg", b"image")])
                )

        loader.assert_not_called()
        self.assertEqual(response["files_processed"], ["front_bumper_damage.jpg"])
        self.assertEqual(len(graph.state["image_files"]), 1)
        self.assertIn("No textual claim documents", graph.state["raw_documents"])

    def test_damage_photo_is_private_graph_input_not_ocr_text_or_public_path(self):
        graph = CapturingGraph()

        def load_only_text_document(path: str):
            if path.endswith("claim_form.txt"):
                return {
                    "filename": "claim_form.txt",
                    "file_type": "text",
                    "content_type": "digital_document",
                    "extraction_method": "native_text",
                    "pages": 1,
                    "text": "front bumper damage",
                }
            raise AssertionError("Damage photos must not enter the OCR document loader.")

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main, "load_document", side_effect=load_only_text_document), patch.object(main, "claim_graph", graph):
                response = asyncio.run(
                    main.process_claim(
                        [
                            FakeUpload("claim_form.txt", b"claim"),
                            FakeUpload("front_bumper_damage.jpg", b"image"),
                        ]
                    )
                )

        self.assertEqual(response["visual_analysis"]["images_analyzed"], ["front_bumper_damage.jpg"])
        self.assertEqual(response["cross_modal_analysis"]["cross_modal_status"], "STRONG_ALIGNMENT")
        self.assertNotIn("path", response["document_metadata"][1])
        self.assertEqual(len(graph.state["image_files"]), 1)
        self.assertNotIn("front_bumper_damage.jpg", graph.state["raw_documents"])

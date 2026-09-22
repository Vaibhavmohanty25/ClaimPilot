import os
import sys
import unittest
from pathlib import Path

from app.agents.vision_agent import analyze_visual_evidence


@unittest.skipUnless(
    os.getenv("RUN_LIVE_MULTIMODAL_TESTS") == "1" and "tests.test_live_multimodal" in sys.argv,
    "Explicitly run tests.test_live_multimodal with RUN_LIVE_MULTIMODAL_TESTS=1 to call Groq.",
)
class LiveMultimodalTests(unittest.TestCase):
    def test_configured_groq_vision_model_analyzes_a_claim_photo(self):
        image_path = os.getenv("LIVE_MULTIMODAL_IMAGE_PATH")
        self.assertTrue(image_path, "Set LIVE_MULTIMODAL_IMAGE_PATH to a JPG, PNG, or WEBP claim photo.")
        self.assertTrue(Path(image_path).is_file())

        result = analyze_visual_evidence(
            [{"filename": Path(image_path).name, "path": image_path}]
        )

        self.assertEqual(result["images_analyzed"], [Path(image_path).name])
        self.assertIn("visible_damage", result)
        self.assertGreater(result["visual_confidence"], 0)
        self.assertFalse(any("could not be validated" in flag or "Groq" in flag for flag in result["visual_risk_flags"]))

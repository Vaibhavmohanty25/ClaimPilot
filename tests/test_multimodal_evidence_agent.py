import unittest

from app.agents.multimodal_evidence_agent import analyze_cross_modal_evidence


class MultimodalEvidenceAgentTests(unittest.TestCase):
    def test_no_photos_is_insufficient_visual_evidence_not_unsupported(self):
        result = analyze_cross_modal_evidence(
            {"repair_estimate_items": [{"item": "Rear bumper replacement", "amount": 12000}]},
            {"supported_claim_items": [], "unsupported_claim_items": []},
            {
                "images_analyzed": [],
                "visible_damage": [],
                "regions_not_visible": [],
                "visual_confidence": 0.0,
            },
        )

        self.assertEqual(result["cross_modal_status"], "INSUFFICIENT_VISUAL_EVIDENCE")
        self.assertEqual(result["visually_unsupported_items"], [])


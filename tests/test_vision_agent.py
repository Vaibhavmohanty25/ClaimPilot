import unittest

from app.agents.vision_agent import analyze_visual_evidence


class VisionAgentTests(unittest.TestCase):
    def test_no_images_returns_neutral_structured_visual_result(self):
        result = analyze_visual_evidence([])

        self.assertEqual(result["images_analyzed"], [])
        self.assertEqual(result["visible_damage"], [])
        self.assertEqual(result["regions_not_visible"], [])
        self.assertEqual(result["visual_confidence"], 0.0)
        self.assertFalse(result["requires_human_review"])


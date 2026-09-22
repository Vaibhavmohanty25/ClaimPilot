import unittest
from unittest.mock import patch

from app.graph import claims_graph as graph_module


class ClaimGraphMultimodalTests(unittest.TestCase):
    def test_visual_node_returns_neutral_result_without_damage_photos(self):
        result = graph_module.visual_node({"image_files": []})

        self.assertEqual(result["visual_analysis"]["images_analyzed"], [])
        self.assertFalse(result["visual_analysis"]["requires_human_review"])

    def test_cross_modal_node_receives_prior_evidence_and_visual_findings(self):
        expected = {"cross_modal_status": "STRONG_ALIGNMENT"}
        state = {
            "claim_reconstruction": {"reported_damage": ["front bumper"]},
            "evidence_analysis": {"evidence_status": "STRONG"},
            "visual_analysis": {"images_analyzed": ["front.jpg"]},
        }

        with patch.object(graph_module, "analyze_cross_modal_evidence", return_value=expected) as analysis:
            result = graph_module.cross_modal_node(state)

        self.assertEqual(result["cross_modal_analysis"], expected)
        self.assertEqual(analysis.call_args.args[0], state["claim_reconstruction"])
        self.assertEqual(analysis.call_args.args[1], state["evidence_analysis"])
        self.assertEqual(analysis.call_args.args[2], state["visual_analysis"])


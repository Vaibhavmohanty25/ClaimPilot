import json
import unittest
from unittest.mock import patch

from app.agents.critic_agent import critique_adjudication
from app.agents.multimodal_evidence_agent import analyze_cross_modal_evidence, no_visual_evidence_result
from app.graph import claims_graph as graph_module


class PhaseTwoScenarioTests(unittest.TestCase):
    def test_strong_multimodal_alignment_is_preserved(self):
        response = {
            "cross_modal_status": "STRONG_ALIGNMENT",
            "cross_modal_confidence": 0.92,
            "supported_items": ["Front bumper replacement", "Left headlamp assembly"],
            "partially_supported_items": [],
            "visually_unsupported_items": [],
            "unverifiable_items": [],
            "cross_modal_contradictions": [],
            "risk_flags": [],
            "requires_human_review": False,
        }
        visual = {
            "images_analyzed": ["front.jpg"],
            "visual_confidence": 0.95,
            "visible_damage": [{"region": "front_bumper", "confidence": 0.95}, {"region": "left_headlamp", "confidence": 0.95}],
            "regions_not_visible": [],
            "regions_visible_intact": [],
        }
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value=json.dumps({**no_visual_evidence_result(), **response})):
            result = analyze_cross_modal_evidence({}, {}, visual)

        self.assertEqual(result["cross_modal_status"], "STRONG_ALIGNMENT")
        self.assertEqual(result["visually_unsupported_items"], [])

    def test_region_not_visible_is_moved_from_unsupported_to_unverifiable(self):
        response = {
            "cross_modal_status": "CONTRADICTORY",
            "visually_unsupported_items": ["Rear bumper replacement"],
            "unverifiable_items": [],
        }
        visual = {
            "images_analyzed": ["front.jpg"],
            "visible_damage": [{"region": "front_bumper"}],
            "regions_not_visible": ["rear_bumper"],
            "regions_visible_intact": [],
        }
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value=json.dumps({**no_visual_evidence_result(), **response})):
            result = analyze_cross_modal_evidence({}, {}, visual)

        self.assertEqual(result["visually_unsupported_items"], [])
        self.assertIn("Rear bumper replacement", result["unverifiable_items"])

    def test_visible_intact_rear_bumper_remains_visually_unsupported(self):
        response = {
            "cross_modal_status": "CONTRADICTORY",
            "visually_unsupported_items": ["Rear bumper replacement"],
            "unverifiable_items": [],
        }
        visual = {
            "images_analyzed": ["rear.jpg"],
            "visual_confidence": 0.95,
            "visible_damage": [],
            "regions_not_visible": [],
            "regions_visible_intact": ["rear_bumper"],
        }
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value=json.dumps({**no_visual_evidence_result(), **response})):
            result = analyze_cross_modal_evidence({}, {}, visual)

        self.assertEqual(result["visually_unsupported_items"], ["Rear bumper replacement"])

    def test_no_image_phase_one_graph_flow_remains_available(self):
        phase_one_result = {
            "claim_reconstruction": {"repair_estimate_items": []},
            "policy_context": [],
            "coverage_analysis": {"coverage_status": "LIKELY_COVERED", "applicable_deductible": 5000},
            "evidence_analysis": {"evidence_status": "STRONG"},
            "missing_information": {"claim_readiness": "READY", "ready_for_adjudication": True},
            "adjudication": {"recommendation": "APPROVE", "recommended_payable_amount": 49000},
            "critic_feedback": {"verification_status": "VERIFIED", "final_recommendation_valid": True},
        }
        with patch.object(graph_module, "reconstruct_claim", return_value=phase_one_result["claim_reconstruction"]), patch.object(graph_module, "analyze_policy", return_value={"policy_context": [], "coverage_analysis": phase_one_result["coverage_analysis"]}), patch.object(graph_module, "analyze_evidence", return_value=phase_one_result["evidence_analysis"]), patch.object(graph_module, "analyze_missing_information", return_value=phase_one_result["missing_information"]), patch.object(graph_module, "adjudicate_claim", return_value=phase_one_result["adjudication"]), patch.object(graph_module, "critique_adjudication", return_value=phase_one_result["critic_feedback"]):
            result = graph_module.build_claim_graph().invoke({"claim_id": "CLM-TEST", "raw_documents": "text claim", "image_files": []})

        self.assertEqual(result["coverage_analysis"]["coverage_status"], "LIKELY_COVERED")
        self.assertEqual(result["visual_analysis"]["images_analyzed"], [])
        self.assertEqual(result["cross_modal_analysis"]["cross_modal_status"], "INSUFFICIENT_VISUAL_EVIDENCE")
        self.assertEqual(result["adjudication"]["recommended_payable_amount"], 49000)
        self.assertTrue(result["critic_feedback"]["final_recommendation_valid"])

    def test_critic_rejects_adjudication_that_approves_visually_unsupported_rear_bumper(self):
        llm_response = json.dumps(
            {
                "verification_status": "VERIFIED",
                "final_recommendation_valid": True,
                "issues_found": [],
            }
        )
        with patch("app.agents.critic_agent.generate_text", return_value=llm_response):
            result = critique_adjudication(
                {}, {}, {}, {},
                {"supported_damage_items": ["Rear bumper replacement"], "recommendation": "APPROVE"},
                {"visually_unsupported_items": ["Rear bumper replacement"]},
            )

        self.assertEqual(result["verification_status"], "REVISION_REQUIRED")
        self.assertFalse(result["final_recommendation_valid"])

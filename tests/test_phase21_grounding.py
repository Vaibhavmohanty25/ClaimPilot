import json
import unittest
from unittest.mock import patch

from app.agents.adjudication_agent import adjudicate_claim
from app.agents.critic_agent import critique_adjudication
from app.agents.evidence_agent import analyze_evidence
from app.agents.missing_info_agent import analyze_missing_information
from app.agents.multimodal_evidence_agent import analyze_cross_modal_evidence, no_visual_evidence_result
from app.services.evidence_semantics import is_visually_verifiable
from app.services.vision_llm import get_vision_model


GROUNDING = {
    "files_processed": ["claim_form.txt", "police_report.txt", "repair_estimate.txt"],
    "document_metadata": [
        {"filename": "claim_form.txt", "file_type": "text", "extraction_method": "native_text"},
        {"filename": "police_report.txt", "file_type": "text", "extraction_method": "native_text"},
        {"filename": "repair_estimate.txt", "file_type": "text", "extraction_method": "native_text"},
    ],
}
RECONSTRUCTION = {
    "repair_estimate_items": [
        {"item": "Front bumper replacement", "amount": 30000},
        {"item": "Left headlamp assembly", "amount": 18000},
        {"item": "Labour charges", "amount": 6000},
    ],
    "repair_estimate_total": 54000,
    "timeline": [{"source": "claim_form.txt, police_report.txt"}],
}


class Phase21GroundingTests(unittest.TestCase):
    def test_uploaded_parsed_documents_and_labour_cannot_be_marked_missing_or_unsupported(self):
        response = json.dumps({
            "evidence_status": "WEAK", "unsupported_claim_items": ["Labour charges"],
            "supported_claim_items": [], "missing_evidence": ["repair estimate missing", "police report missing"],
        })
        with patch("app.agents.evidence_agent.generate_text", return_value=response):
            result = analyze_evidence(RECONSTRUCTION, {}, **GROUNDING)
        self.assertNotIn("Labour charges", result["unsupported_claim_items"])
        self.assertIn("Labour charges", result["supported_claim_items"])
        self.assertEqual(result["missing_evidence"], [])

    def test_labour_is_not_visually_verifiable_and_not_placed_in_visual_buckets(self):
        self.assertFalse(is_visually_verifiable("Labour charges"))
        response = {**no_visual_evidence_result(), "supported_items": ["Labour charges"],
                    "visually_unsupported_items": ["Labour charges"], "unverifiable_items": ["Labour charges"]}
        visual = {"images_analyzed": ["front.jpg"], "visual_confidence": .95,
                  "visible_damage": [], "regions_not_visible": [], "regions_visible_intact": []}
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value=json.dumps(response)):
            result = analyze_cross_modal_evidence(RECONSTRUCTION, {}, visual)
        self.assertNotIn("Labour charges", result["visually_unsupported_items"])
        self.assertNotIn("Labour charges", result["unverifiable_items"])

    def test_not_visible_headlamp_is_unverifiable_once_and_not_unsupported(self):
        response = {**no_visual_evidence_result(), "visually_unsupported_items": ["Left headlamp assembly"],
                    "unverifiable_items": ["left headlamp", "Left headlamp assembly"]}
        visual = {"images_analyzed": ["front.jpg"], "visual_confidence": .95, "visible_damage": [],
                  "regions_not_visible": ["left_headlamp"], "regions_visible_intact": []}
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value=json.dumps(response)):
            result = analyze_cross_modal_evidence(RECONSTRUCTION, {}, visual)
        self.assertEqual(result["visually_unsupported_items"], [])
        self.assertEqual(len(result["unverifiable_items"]), 1)

    def test_missing_information_does_not_request_present_repair_estimate(self):
        response = json.dumps({"claim_readiness": "NOT_READY", "missing_documents": ["complete repair estimate"],
                               "missing_evidence": ["repair estimate"], "blocking_issues": []})
        with patch("app.agents.missing_info_agent.generate_text", return_value=response):
            result = analyze_missing_information(RECONSTRUCTION, {}, {}, {}, **GROUNDING)
        self.assertEqual(result["missing_documents"], [])
        self.assertEqual(result["missing_evidence"], [])

    def test_not_ready_with_blocker_has_no_final_payable_amount(self):
        response = json.dumps({"recommendation": "REQUEST_MORE_INFORMATION", "supported_repair_items": [
            {"item": "Front bumper replacement", "amount": 30000}]})
        with patch("app.agents.adjudication_agent.generate_text", return_value=response):
            result = adjudicate_claim(RECONSTRUCTION, {"applicable_deductible": 5000}, {},
                                      {"claim_readiness": "NOT_READY", "blocking_issues": ["Need material evidence"]})
        self.assertIsNone(result["recommended_payable_amount"])

    def test_critic_rejects_false_missing_estimate_and_false_visual_labour_claim(self):
        response = json.dumps({"verification_status": "VERIFIED", "final_recommendation_valid": True, "issues_found": []})
        with patch("app.agents.critic_agent.generate_text", return_value=response):
            result = critique_adjudication(RECONSTRUCTION, {},
                {"missing_evidence": ["repair estimate missing", "Labour unsupported because no photo"]},
                {"missing_documents": ["repair estimate"]}, {"recommended_payable_amount": 0}, {}, **GROUNDING)
        self.assertEqual(result["verification_status"], "REVISION_REQUIRED")
        self.assertFalse(result["final_recommendation_valid"])

    def test_default_live_vision_model_is_preserved(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(get_vision_model(), "qwen/qwen3.8-27b")

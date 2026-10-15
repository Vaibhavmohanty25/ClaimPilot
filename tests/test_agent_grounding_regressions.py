import json
import unittest
from unittest.mock import patch

from app.agents.critic_agent import critique_adjudication
from app.graph.claims_graph import claim_graph, critic_node
from app.services.evidence_semantics import apply_visual_visibility_guard, is_visually_verifiable


VERIFIED = {"verification_status": "VERIFIED", "final_recommendation_valid": True,
            "issues_found": []}


class AgentGroundingRegressionTests(unittest.TestCase):
    def test_graph_preserves_uploaded_document_grounding_through_all_agents(self):
        metadata = [{"filename": "repair_estimate.pdf", "extraction_method": "native_text"},
                    {"filename": "police_report.pdf", "extraction_method": "ocr"}]
        evidence = {"supported_claim_items": [], "unsupported_claim_items": [],
                    "missing_evidence": ["Repair estimate missing", "Police report missing"]}
        missing = {"claim_readiness": "NOT_READY", "ready_for_adjudication": False,
                   "missing_documents": ["Repair estimate", "Police report"],
                   "blocking_issues": ["Repair estimate missing"]}
        with patch("app.graph.claims_graph.reconstruct_claim", return_value={}), \
             patch("app.graph.claims_graph.analyze_policy", return_value={"policy_context": [], "coverage_analysis": {}}), \
             patch("app.agents.evidence_agent.generate_text", return_value=json.dumps(evidence)), \
             patch("app.agents.missing_info_agent.generate_text", return_value=json.dumps(missing)), \
             patch("app.agents.adjudication_agent.generate_text", return_value=json.dumps({"recommendation": "REQUEST_MORE_INFORMATION"})), \
             patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
            result = claim_graph.invoke({"raw_documents": "Parsed evidence", "document_metadata": metadata,
                                         "image_files": []})
        self.assertEqual(result["evidence_analysis"]["missing_evidence"], [])
        self.assertEqual(result["missing_information"]["missing_documents"], [])
        self.assertEqual(result["missing_information"]["blocking_issues"], [])

    def test_graph_critic_uses_uploaded_metadata_to_detect_false_absence(self):
        state = {"claim_reconstruction": {}, "coverage_analysis": {},
                 "evidence_analysis": {"risk_flags": ["Police report not supplied"]},
                 "missing_information": {}, "adjudication": {},
                 "document_metadata": [{"filename": "police_report.pdf", "extraction_method": "ocr"}]}
        with patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
            result = critic_node(state)["critic_feedback"]
        self.assertEqual(result["verification_status"], "REVISION_REQUIRED")

    def test_critic_does_not_mix_document_support_with_unrelated_missing_evidence(self):
        with patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
            result = critique_adjudication(
                {"repair_estimate_total": 30000, "timeline": [{"source": "police_report.pdf"}]}, {},
                {"supported_claim_items": ["Repair estimate and police report support collision damage"],
                 "missing_evidence": ["Driver licence missing"]}, {}, {}, {})
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["issues_found"], [])

    def test_critic_does_not_mix_documented_labour_with_unseen_damage(self):
        with patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
            result = critique_adjudication(
                {"repair_estimate_items": [{"item": "Labour charges", "amount": 6000}]}, {},
                {"supported_claim_items": ["Labour charges"],
                 "unsupported_claim_items": ["Left headlamp unsupported because no visual evidence"]}, {}, {}, {})
        self.assertEqual(result["verification_status"], "VERIFIED")

    def test_critic_still_catches_individual_false_missing_document_assertions(self):
        for document in ("Repair estimate", "Police report"):
            with self.subTest(document=document), \
                 patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
                result = critique_adjudication({}, {}, {"missing_evidence": [document]}, {}, {}, {},
                                               files_processed=["repair_estimate.pdf", "police_report.pdf"])
                self.assertEqual(result["verification_status"], "REVISION_REQUIRED")

    def test_visual_only_filenames_do_not_count_as_parsed_documents(self):
        metadata = [{"filename": "repair_estimate.jpg", "file_type": "image", "content_type": "damage_photo", "extraction_method": "vision_pending"},
                    {"filename": "police_report.jpg", "file_type": "image", "content_type": "unknown_image", "extraction_method": "vision_pending"}]
        missing_docs = ["Repair estimate", "Police report"]
        with patch("app.graph.claims_graph.reconstruct_claim", return_value={}), \
             patch("app.graph.claims_graph.analyze_policy", return_value={"policy_context": [], "coverage_analysis": {}}), \
             patch("app.agents.evidence_agent.generate_text", return_value=json.dumps({"missing_evidence": missing_docs})), \
             patch("app.agents.missing_info_agent.generate_text", return_value=json.dumps({"missing_documents": missing_docs, "claim_readiness": "NOT_READY", "ready_for_adjudication": False})), \
             patch("app.agents.adjudication_agent.generate_text", return_value=json.dumps({"recommendation": "REQUEST_MORE_INFORMATION"})), \
             patch("app.agents.critic_agent.generate_text", return_value=json.dumps(VERIFIED)):
            result = claim_graph.invoke({"raw_documents": "No documents supplied", "document_metadata": metadata,
                                         "files_processed": [item["filename"] for item in metadata], "image_files": []})
        self.assertEqual(result["missing_information"]["missing_documents"], missing_docs)
        self.assertEqual(result["evidence_analysis"]["missing_evidence"], missing_docs)
        self.assertEqual(result["critic_feedback"]["verification_status"], "VERIFIED")

    def test_documentary_labour_is_not_deduplicated_with_physical_component(self):
        analysis = {"supported_items": ["Front bumper replacement", "Front bumper labour charges"]}
        visual = {"visual_confidence": .95, "vehicle_visible": True,
                  "visible_damage": [{"region": "front_bumper", "confidence": .95}]}
        result = apply_visual_visibility_guard(analysis, visual)
        self.assertEqual(result["supported_items"], ["Front bumper replacement", "Front bumper labour charges"])

    def test_administrative_charges_do_not_require_photographs(self):
        self.assertFalse(is_visually_verifiable("Administrative charges"))


if __name__ == "__main__":
    unittest.main()

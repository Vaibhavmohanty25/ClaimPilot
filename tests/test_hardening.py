import asyncio
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import httpx
from groq import APIStatusError, APITimeoutError
from PIL import Image, ImageDraw

from app.agents.vision_agent import analyze_visual_evidence, neutral_visual_analysis
from app.agents.adjudication_agent import adjudicate_claim
from app.services.settlement_calculator import calculate_payable_amount
from app.services.evidence_semantics import apply_visual_visibility_guard
from app.services import llm, vision_llm
from app.multimodal.file_classifier import classify_file


def visual_payload(name="front.jpg", **changes):
    result = neutral_visual_analysis()
    result.update(images_analyzed=[name], vehicle_visible=True,
                  vehicle_regions_visible=["front_bumper"], visual_confidence=0.95)
    result.update(changes)
    return result


def damage(name="front.jpg"):
    return dict(region="front_bumper", damage_type="dent", severity="moderate",
                confidence=0.9, source_image=name, description="Visible dent")


class SettlementHardeningTests(unittest.TestCase):
    def test_rejects_untrusted_numbers_and_missing_total(self):
        for values, deductible in [(None, 0), ([float("nan")], 0), ([float("inf")], 0),
                                   ([1], float("nan")), ([True], 0), (["10"], 0),
                                   ([1], -1), ([1], True), ([-1], 0)]:
            with self.subTest(values=values, deductible=deductible):
                self.assertIsNone(calculate_payable_amount(values, deductible))

    def test_decimal_arithmetic_and_zero_boundaries(self):
        for values, deductible, expected in [([0.1, 0.2], 0, 0.3),
                ([Decimal("10.01")], Decimal("0.01"), 10), ([10], 20, 0),
                ([10], 10, 0), ([0], 0, 0), ([], 0, 0)]:
            with self.subTest(values=values):
                self.assertEqual(calculate_payable_amount(values, deductible), expected)

    def test_missing_supported_items_is_unknown_not_zero(self):
        with patch("app.agents.adjudication_agent.generate_text", return_value='{"recommended_payable_amount": 500}'):
            self.assertIsNone(adjudicate_claim({}, {"applicable_deductible": 0}, {}, {})["recommended_payable_amount"])


class VisionHardeningTests(unittest.TestCase):
    def analyze(self, response, files=None):
        with patch("app.agents.vision_agent.generate_vision_json", return_value=response):
            return analyze_visual_evidence(files or [{"filename": "front.jpg", "path": "front.jpg"}])

    def test_bad_structures_are_neutral_review_results(self):
        malformed = ["not json", "", None, "null", "[]", "{}",
                     json.dumps(visual_payload(visual_confidence=2)),
                     json.dumps(visual_payload(visual_confidence=True)),
                     json.dumps(visual_payload(visible_damage=["dent"])),
                     json.dumps(visual_payload(visible_damage=[dict(damage(), source_image="other.jpg")])),
                     json.dumps(visual_payload(visible_damage=[{"region": "front_bumper"}]))]
        for response in malformed:
            with self.subTest(response=response):
                result = self.analyze(response)
                self.assertTrue(result["requires_human_review"])
                self.assertEqual(result["visible_damage"], [])
                self.assertEqual(result["visual_confidence"], 0)

    def test_fences_unknown_fields_and_duplicate_findings(self):
        response = visual_payload(visible_damage=[damage(), damage()], extra="private")
        result = self.analyze("```JSON\n" + json.dumps(response) + "\n```")
        self.assertEqual(len(result["visible_damage"]), 1)
        self.assertEqual(result["visible_damage"][0]["source_image"], "front.jpg")
        self.assertNotIn("extra", result)

    def test_identical_files_are_analyzed_once_without_inflating_confidence(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first.jpg", Path(directory) / "second.jpg"
            first.write_bytes(b"identical image bytes")
            second.write_bytes(first.read_bytes())
            with patch("app.agents.vision_agent.generate_vision_json", return_value=json.dumps(visual_payload("first.jpg", visible_damage=[damage("first.jpg")]))) as provider:
                result = analyze_visual_evidence([{"filename": path.name, "path": str(path)} for path in [first, second]])
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(result["visual_confidence"], 0.95)
        self.assertEqual(len(result["visible_damage"]), 1)
        self.assertEqual(result["duplicate_images"], [{"source_image": "second.jpg", "duplicate_of": "first.jpg"}])

    def test_one_bad_response_preserves_good_image_findings(self):
        with patch("app.agents.vision_agent.generate_vision_json", side_effect=["bad", json.dumps(visual_payload("good.jpg", visible_damage=[damage("good.jpg")]))]):
            result = analyze_visual_evidence([{"filename": n, "path": n} for n in ["bad.jpg", "good.jpg"]])
        self.assertEqual(result["visible_damage"][0]["source_image"], "good.jpg")
        self.assertTrue(result["requires_human_review"])

    def test_provider_failure_is_neutral(self):
        with patch("app.agents.vision_agent.generate_vision_json", side_effect=RuntimeError("private request")):
            result = analyze_visual_evidence([{"filename": "front.jpg", "path": "front.jpg"}])
        self.assertTrue(result["requires_human_review"])
        self.assertNotIn("private request", json.dumps(result))

    def test_multiple_images_preserve_conflict_and_stronger_evidence(self):
        responses = [json.dumps(visual_payload(visible_damage=[damage()])),
                     json.dumps(visual_payload("rear.jpg", regions_visible_intact=["front_bumper"])),
                     json.dumps(visual_payload("blur.jpg", visual_confidence=0.1,
                                              image_quality_issues=["blurred"], regions_not_visible=["front_bumper"]))]
        with patch("app.agents.vision_agent.generate_vision_json", side_effect=responses):
            result = analyze_visual_evidence([{"filename": n, "path": n} for n in ["front.jpg", "rear.jpg", "blur.jpg"]])
        self.assertEqual(result["visible_damage"][0]["source_image"], "front.jpg")
        self.assertTrue(result["visual_contradictions"])
        self.assertNotIn("front_bumper", result["regions_not_visible"])
        self.assertGreaterEqual(result["visual_confidence"], 0.9)

    def test_provider_limit_fails_before_any_request(self):
        with patch.object(vision_llm.client.chat.completions, "create") as request:
            with self.assertRaisesRegex(ValueError, "3"):
                vision_llm.generate_vision_json("json", ["x.jpg"] * 4)
        request.assert_not_called()

    def test_missing_and_unsupported_images_fail_clearly(self):
        with self.assertRaises(ValueError):
            vision_llm.encode_image_data_url("x.gif")
        with self.assertRaises(FileNotFoundError):
            vision_llm.encode_image_data_url("missing.jpg")


class SemanticHardeningTests(unittest.TestCase):
    def test_low_confidence_poor_quality_unseen_and_unknown_regions_are_unverifiable(self):
        for changes, item in [({"visual_confidence": 0.2}, "Front bumper"),
                              ({"image_quality_issues": ["blurred"]}, "Front bumper"),
                              ({"regions_visible_intact": []}, "Front bumper"),
                              ({}, "Unknown assembly")]:
            visual = visual_payload(regions_visible_intact=["front_bumper"])
            visual.update(changes)
            with self.subTest(changes=changes, item=item):
                result = apply_visual_visibility_guard({"visually_unsupported_items": [item]}, visual)
                self.assertEqual(result["visually_unsupported_items"], [])
                self.assertEqual(result["unverifiable_items"], [item])

    def test_visible_damage_cannot_be_called_intact(self):
        visual = visual_payload(visible_damage=[damage()], regions_visible_intact=["front_bumper"])
        result = apply_visual_visibility_guard({"visually_unsupported_items": ["Front bumper"]}, visual)
        self.assertEqual(result["visually_unsupported_items"], [])


class ProviderHardeningTests(unittest.TestCase):
    def test_both_providers_retry_transient_errors_and_sanitize_permanent_errors(self):
        from types import SimpleNamespace
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])
        for module in [llm, vision_llm]:
            for status in [429, 500, 503, 400, 401, 404, 422]:
                error = APIStatusError("secret private contents", response=httpx.Response(status, request=httpx.Request("POST", "https://example.com")), body={"error": {"code": "model_not_found"}} if status == 404 else {})
                with self.subTest(module=module.__name__, status=status), patch.object(module.client.chat.completions, "create", side_effect=[error, response]) as create, patch("time.sleep") as sleep, patch.object(vision_llm, "encode_image_data_url", return_value="data:image/png;base64,eA=="):
                    call = (lambda: module.generate_text("secret")) if module is llm else (lambda: module.generate_vision_json("secret", ["x.png"]))
                    if status in [429, 500, 503]:
                        self.assertEqual(call(), "{}")
                        self.assertEqual(create.call_count, 2)
                        sleep.assert_called_once_with(1)
                    else:
                        with self.assertRaises(RuntimeError) as caught:
                            call()
                        self.assertNotIn("secret", str(caught.exception))
                        self.assertEqual(create.call_count, 1)

    def test_timeouts_have_bounded_exponential_backoff(self):
        for module in [llm, vision_llm]:
            error = APITimeoutError(request=httpx.Request("POST", "https://example.com"))
            with self.subTest(module=module.__name__), patch.object(module.client.chat.completions, "create", side_effect=error) as create, patch("time.sleep") as sleep, patch.object(vision_llm, "encode_image_data_url", return_value="data:image/png;base64,eA=="):
                with self.assertRaises(RuntimeError):
                    if module is llm:
                        module.generate_text("secret")
                    else:
                        module.generate_vision_json("secret", ["x.png"])
                self.assertEqual(create.call_count, 3)
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])


class RoutingHardeningTests(unittest.TestCase):
    def test_accident_like_pixels_do_not_trigger_ocr_even_with_document_name(self):
        import random
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claim_form.png"
            randomizer = random.Random(42)
            image = Image.frombytes("RGB", (200, 200), randomizer.randbytes(200 * 200 * 3))
            image.save(path)
            with patch("app.services.ocr_service.extract_text_from_image", side_effect=AssertionError("Must not OCR photo")):
                result = classify_file(str(path))
            self.assertEqual(result["content_type"], "damage_photo")

    def test_filename_does_not_turn_invalid_image_into_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claim_form.png"
            path.write_bytes(b"invalid")
            self.assertEqual(classify_file(str(path))["content_type"], "unknown_image")

    def test_document_pixels_route_without_filename_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "IMG_123.png"
            image = Image.new("RGB", (600, 800), "white")
            draw = ImageDraw.Draw(image)
            for y in range(40, 700, 30):
                draw.text((40, y), "Repair estimate front bumper replacement amount 1000", fill="black")
            image.save(path)
            with patch("app.services.ocr_service.extract_text_from_image", return_value="Repair estimate\nFront bumper replacement 1000\nLabour charges 100\nTotal 1100"):
                result = classify_file(str(path))
            self.assertEqual(result["content_type"], "document_image")


class PrivacyHardeningTests(unittest.TestCase):
    def test_public_metadata_excludes_ocr_text_and_temp_paths(self):
        from app import main
        from tests.test_api_multimodal import FakeUpload
        document = dict(file_type="pdf", content_type="scanned_or_mixed_pdf", extraction_method="mixed", pages=1,
                        text="POLICE report", page_details=[dict(page_number=1, extraction_method="ocr", text="private OCR", path="/tmp/ocr.png")])
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main, "load_document", return_value=document), patch.object(main.claim_graph, "invoke", return_value={}):
            result = asyncio.run(main.process_claim([FakeUpload("police.pdf", b"pdf")]))
        self.assertEqual(result["document_metadata"][0]["page_details"], [{"page_number": 1, "extraction_method": "ocr"}])

    def test_duplicate_upload_names_have_distinct_paths_and_sources(self):
        from app import main
        from tests.test_api_multimodal import FakeUpload, CapturingGraph
        graph = CapturingGraph()
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main, "claim_graph", graph):
            result = asyncio.run(main.process_claim([FakeUpload("front.jpg", b"first"), FakeUpload("front.jpg", b"second")]))
            paths = [item["path"] for item in graph.state["image_files"]]
            self.assertEqual(len(set(paths)), 2)
            self.assertEqual([Path(path).read_bytes() for path in paths], [b"first", b"second"])
        self.assertEqual(result["files_processed"], ["front.jpg", "2-front.jpg"])

    def test_actual_http_error_is_private_and_count_limit_is_400(self):
        from fastapi.testclient import TestClient
        from app import main
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "UPLOAD_DIR", Path(directory)):
            response = TestClient(main.app).post("/claims/process", files=[("files", (f"{i}.jpg", b"invalid", "image/jpeg")) for i in range(4)])
        self.assertEqual(response.status_code, 400)
        self.assertIn("3 images", response.json()["detail"])

    def test_api_exception_does_not_expose_private_path(self):
        from app import main
        from tests.test_api_multimodal import FakeUpload
        from fastapi import HTTPException
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main, "load_document", side_effect=RuntimeError("C:\\private\\uploads\\secret.txt API_KEY=secret")):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(main.process_claim([FakeUpload("claim.txt", b"claim")]))
        self.assertNotIn("private", caught.exception.detail)
        self.assertNotIn("secret", caught.exception.detail)

    def test_api_sanitizes_nested_metadata_and_model_echoes(self):
        from app import main
        from tests.test_api_multimodal import FakeUpload
        with tempfile.TemporaryDirectory() as directory, patch.object(main, "UPLOAD_DIR", Path(directory)), patch.object(main.claim_graph, "invoke", return_value={"policy_context": [{"source": "C:\\private\\policy.txt"}], "critic_feedback": {"raw_response": "private", "issues_found": ["File /tmp/private/file.txt unreadable"]}}):
            result = asyncio.run(main.process_claim([FakeUpload("claim.txt", b"claim text")]))
        serialized = json.dumps(result)
        self.assertNotIn("C:\\\\private", serialized)
        self.assertNotIn("/tmp/private", serialized)
        self.assertNotIn("raw_response", serialized)


class AdditionalSemanticTests(unittest.TestCase):
    def test_low_quality_vision_does_not_manufacture_contradictions(self):
        with patch("app.agents.vision_agent.generate_vision_json", return_value=json.dumps(visual_payload(visual_confidence=0.1, image_quality_issues=["blur"], visual_contradictions=["Front bumper damage not seen in blur"]))):
            result = analyze_visual_evidence([{"filename": "front.jpg", "path": "front.jpg"}])
        self.assertEqual(result["visual_contradictions"], [])
        self.assertTrue(result["requires_human_review"])

    def test_empty_contradictions_cannot_leave_contradictory_status(self):
        result = apply_visual_visibility_guard({"cross_modal_status": "CONTRADICTORY", "cross_modal_contradictions": []}, visual_payload(visual_confidence=0.1, image_quality_issues=["blur"]))
        self.assertNotEqual(result["cross_modal_status"], "CONTRADICTORY")

    def test_incomplete_cross_modal_response_requires_review(self):
        from app.agents.multimodal_evidence_agent import analyze_cross_modal_evidence
        with patch("app.agents.multimodal_evidence_agent.generate_text", return_value="{}"):
            result = analyze_cross_modal_evidence({}, {}, visual_payload())
        self.assertTrue(result["requires_human_review"])
        self.assertIn("cross_modal_status", result)

    def test_blurry_intact_claim_does_not_contradict_clear_damage(self):
        responses = [json.dumps(visual_payload(visible_damage=[damage()])), json.dumps(visual_payload("blur.jpg", visual_confidence=0.1, image_quality_issues=["blur"], regions_visible_intact=["front_bumper"]))]
        with patch("app.agents.vision_agent.generate_vision_json", side_effect=responses):
            result = analyze_visual_evidence([{"filename": name, "path": name} for name in ["front.jpg", "blur.jpg"]])
        self.assertEqual(result["visual_contradictions"], [])
        self.assertEqual(result["visible_damage"][0]["source_image"], "front.jpg")

    def test_low_quality_is_not_a_cross_modal_contradiction(self):
        visual = visual_payload(visual_confidence=0.1, image_quality_issues=["blurred"])
        result = apply_visual_visibility_guard({"cross_modal_status": "CONTRADICTORY", "cross_modal_contradictions": ["Front bumper damage not seen in blurry image"]}, visual)
        self.assertEqual(result["cross_modal_contradictions"], [])
        self.assertNotEqual(result["cross_modal_status"], "CONTRADICTORY")

    def test_low_quality_cannot_support_an_item_or_inflate_confidence(self):
        visual = visual_payload(visual_confidence=0.1, image_quality_issues=["blurred"], visible_damage=[damage()])
        result = apply_visual_visibility_guard({"supported_items": ["Front bumper"], "cross_modal_confidence": 0.99}, visual)
        self.assertEqual(result["supported_items"], [])
        self.assertIn("Front bumper", result["unverifiable_items"])
        self.assertLessEqual(result["cross_modal_confidence"], 0.1)

    def test_same_observation_cannot_be_both_intact_and_unseen(self):
        visual = visual_payload(regions_visible_intact=["front_bumper"], regions_not_visible=["front_bumper"])
        result = apply_visual_visibility_guard({"visually_unsupported_items": ["Front bumper"]}, visual)
        self.assertEqual(result["visually_unsupported_items"], [])

    def test_strong_intact_view_survives_another_blurred_view(self):
        strong = visual_payload(regions_visible_intact=["front_bumper"])
        blurred = visual_payload("blur.jpg", visual_confidence=0.1, image_quality_issues=["blur"], regions_not_visible=["front_bumper"])
        visual = visual_payload(image_quality_issues=["blur"], image_observations=[strong, blurred])
        result = apply_visual_visibility_guard({"visually_unsupported_items": ["Front bumper"]}, visual)
        self.assertEqual(result["visually_unsupported_items"], ["Front bumper"])

    def test_low_confidence_damage_does_not_override_a_clear_intact_view(self):
        strong = visual_payload(regions_visible_intact=["front_bumper"])
        blurred = visual_payload("blur.jpg", visual_confidence=0.1, image_quality_issues=["blur"], visible_damage=[damage("blur.jpg")])
        visual = visual_payload(image_observations=[strong, blurred])
        result = apply_visual_visibility_guard({"visually_unsupported_items": ["Front bumper"]}, visual)
        self.assertEqual(result["visually_unsupported_items"], ["Front bumper"])

    def test_critic_requires_review_when_multimodal_failure_was_ignored(self):
        from app.agents.critic_agent import critique_adjudication
        with patch("app.agents.critic_agent.generate_text", return_value='{"verification_status":"VERIFIED","final_recommendation_valid":true}'):
            result = critique_adjudication({}, {}, {}, {}, {"recommendation": "APPROVE", "human_review_required": False}, {"requires_human_review": True})
        self.assertFalse(result["final_recommendation_valid"])


class OfflineGraphRegressionTests(unittest.TestCase):
    def run_graph(self, images):
        from contextlib import ExitStack
        from app.graph.claims_graph import build_claim_graph
        from app.agents import claim_reconstruction, evidence_agent, missing_info_agent, adjudication_agent, critic_agent
        payloads = [
            (claim_reconstruction, {"reported_damage": ["Front bumper"], "repair_estimate_items": [{"item": "Front bumper", "amount": 100}]}),
            (evidence_agent, {"evidence_status": "STRONG", "supported_claim_items": ["Front bumper"]}),
            (missing_info_agent, {"ready_for_adjudication": True}),
            (adjudication_agent, {"recommendation": "APPROVE", "human_review_required": False, "supported_repair_items": [{"item": "Front bumper", "amount": 100}], "recommended_payable_amount": 999}),
            (critic_agent, {"verification_status": "VERIFIED", "final_recommendation_valid": True}),
        ]
        with ExitStack() as stack:
            for module, payload in payloads:
                stack.enter_context(patch.object(module, "generate_text", return_value=json.dumps(payload)))
            stack.enter_context(patch("app.graph.claims_graph.analyze_policy", return_value={"policy_context": [], "coverage_analysis": {"applicable_deductible": 10}}))
            stack.enter_context(patch("app.agents.vision_agent.generate_vision_json", return_value="malformed"))
            return build_claim_graph().invoke({"claim_id": "CLM-REGRESSION", "raw_documents": "Collision; front bumper repair 100", "image_files": images})

    def test_real_text_agents_keep_valid_no_image_claim_and_deterministic_amount(self):
        result = self.run_graph([])
        self.assertEqual(result["adjudication"]["recommended_payable_amount"], 90)
        self.assertEqual(result["adjudication"]["recommendation"], "APPROVE")
        self.assertFalse(result["adjudication"]["human_review_required"])

    def test_malformed_vision_completes_graph_and_requires_review(self):
        result = self.run_graph([{"filename": "front.jpg", "path": "missing.jpg"}])
        self.assertTrue(result["adjudication"]["human_review_required"])
        self.assertEqual(result["adjudication"]["recommendation"], "ESCALATE_FOR_HUMAN_REVIEW")
        self.assertEqual(result["visual_analysis"]["visible_damage"], [])

    def test_observability_records_stage_claim_duration_without_documents(self):
        with self.assertLogs("claimpilot", level="INFO") as logs:
            self.run_graph([])
        events = [json.loads(record.message) for record in logs.records]
        self.assertTrue(any(event.get("claim_id") == "CLM-REGRESSION" and "duration_ms" in event for event in events))
        self.assertNotIn("Collision", "\n".join(logs.output))

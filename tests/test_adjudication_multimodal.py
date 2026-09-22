import json
import unittest
from unittest.mock import patch

from app.agents.adjudication_agent import adjudicate_claim


class AdjudicationMultimodalTests(unittest.TestCase):
    def test_replaces_llm_payable_amount_with_deterministic_supported_total(self):
        response = json.dumps(
            {
                "recommendation": "APPROVE_WITH_ADJUSTMENT",
                "supported_repair_items": [
                    {"item": "Front bumper replacement", "amount": 30000},
                    {"item": "Left headlamp assembly", "amount": 18000},
                    {"item": "Labour charges", "amount": 6000},
                ],
                "recommended_payable_amount": 999999,
            }
        )

        with patch("app.agents.adjudication_agent.generate_text", return_value=response):
            result = adjudicate_claim(
                {"repair_estimate_items": []},
                {"applicable_deductible": 5000},
                {},
                {},
                {"cross_modal_status": "STRONG_ALIGNMENT"},
            )

        self.assertEqual(result["recommended_payable_amount"], 49000)

    def test_keeps_payable_amount_unknown_when_supported_prices_are_incomplete(self):
        response = json.dumps(
            {
                "recommendation": "APPROVE",
                "supported_repair_items": [
                    {"item": "Front bumper replacement", "amount": None},
                ],
                "recommended_payable_amount": 10000,
            }
        )

        with patch("app.agents.adjudication_agent.generate_text", return_value=response):
            result = adjudicate_claim({}, {"applicable_deductible": 5000}, {}, {}, {})

        self.assertIsNone(result["recommended_payable_amount"])


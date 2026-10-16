"""Model JSON primitives must not crash later graph stages."""
import unittest
from unittest.mock import patch
from app.agents.claim_reconstruction import reconstruct_claim
from app.agents.policy_agent import analyze_policy


class AgentResponseShapeTests(unittest.TestCase):
    def test_reconstruction_non_object_json_returns_reviewable_error(self):
        for response in ('null', '[]', 'true', '42', '"text"'):
            with self.subTest(response=response), patch('app.agents.claim_reconstruction.generate_text', return_value=response):
                result = reconstruct_claim('Motor collision claim')
                self.assertIsInstance(result, dict)
                self.assertIn('error', result)

    def test_policy_non_object_json_returns_uncertain_coverage(self):
        with patch('app.rag.retriever.retrieve_policy_context', return_value=[]):
            for response in ('null', '[]', 'true', '42', '"text"'):
                with self.subTest(response=response), patch('app.agents.policy_agent.generate_text', return_value=response):
                    result = analyze_policy({})['coverage_analysis']
                    self.assertIsInstance(result, dict)
                    self.assertTrue(result['requires_human_review'])
                    self.assertIsNone(result['applicable_deductible'])


if __name__ == '__main__':
    unittest.main()

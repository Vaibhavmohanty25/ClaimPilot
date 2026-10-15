import json
import unittest
from unittest.mock import patch

from app.agents.policy_evidence_agent import analyze_policy_and_evidence
from app.services.provider_retry import ProviderError


def combined_response():
    return {
        'coverage_analysis': {'coverage_status': 'LIKELY_COVERED', 'coverage_confidence': 0.9,
            'reasoning': ['Collision is covered'], 'applicable_deductible': 5000,
            'exclusions_triggered': [], 'policy_evidence': ['SECTION 5'], 'requires_human_review': False},
        'evidence_analysis': {'evidence_status': 'PARTIALLY_SUPPORTED', 'evidence_confidence': 0.8,
            'contradictions': [], 'unsupported_claim_items': ['Labour charges'],
            'supported_claim_items': ['Front bumper'], 'missing_evidence': ['Missing repair estimate'],
            'risk_flags': [], 'requires_human_review': True},
    }


class PolicyEvidenceBatchTests(unittest.TestCase):
    def test_one_call_retains_retrieval_and_applies_document_grounding(self):
        context = [{'text': 'SECTION 5: A deductible of INR 5000 applies.'}]
        claim = {'repair_estimate_items': [{'item': 'Labour charges', 'amount': 100}], 'repair_estimate_total': 100}
        with patch('app.agents.policy_evidence_agent.retrieve_claim_policy_context', return_value=context) as retrieve, patch('app.agents.policy_evidence_agent.generate_text', return_value=json.dumps(combined_response())) as generate:
            result = analyze_policy_and_evidence(claim, document_metadata=[{'filename': 'repair_estimate.pdf'}])
        retrieve.assert_called_once_with(claim)
        generate.assert_called_once()
        self.assertIn('SECTION 5: A deductible of INR 5000 applies.', generate.call_args.args[0])
        self.assertEqual(result['policy_context'], context)
        self.assertEqual(result['coverage_analysis']['applicable_deductible'], 5000)
        self.assertEqual(result['evidence_analysis']['missing_evidence'], [])
        self.assertEqual(result['evidence_analysis']['unsupported_claim_items'], [])
        self.assertIn('Labour charges', result['evidence_analysis']['supported_claim_items'])

    def test_malformed_or_incomplete_batch_fails_without_extra_provider_calls(self):
        for response in ('not json', 'null', '[]', '{}', '{"coverage_analysis":{}}'):
            with self.subTest(response=response), patch('app.agents.policy_evidence_agent.retrieve_claim_policy_context', return_value=[]), patch('app.agents.policy_evidence_agent.generate_text', return_value=response) as generate:
                with self.assertRaises(ProviderError):
                    analyze_policy_and_evidence({})
                generate.assert_called_once()

    def test_invalid_review_flags_and_collections_fail_safely(self):
        for section, field, value in [('coverage_analysis', 'requires_human_review', 'false'), ('evidence_analysis', 'missing_evidence', 'none'), ('coverage_analysis', 'applicable_deductible', True), ('coverage_analysis', 'coverage_confidence', float('nan'))]:
            response = combined_response()
            response[section][field] = value
            with self.subTest(field=field), patch('app.agents.policy_evidence_agent.retrieve_claim_policy_context', return_value=[]), patch('app.agents.policy_evidence_agent.generate_text', return_value=json.dumps(response)):
                with self.assertRaises(ProviderError):
                    analyze_policy_and_evidence({})

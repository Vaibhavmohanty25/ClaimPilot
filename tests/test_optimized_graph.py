import unittest
import json
from unittest.mock import patch

from app.graph import claims_graph as module
from app.agents.multimodal_evidence_agent import no_visual_evidence_result


class OptimizedGraphTests(unittest.TestCase):
    def test_queued_graph_batches_policy_evidence_and_keeps_independent_critic(self):
        claim = {'reported_damage': ['front bumper']}
        batch = {'coverage_analysis': {'applicable_deductible': 5000}, 'policy_context': [{'text': 'policy'}],
                 'evidence_analysis': {'supported_claim_items': ['front bumper']}}
        metadata = [{'filename': 'police_report.jpg', 'extraction_method': 'vision_pending'},
                    {'filename': 'estimate.pdf', 'extraction_method': 'native_text'}]
        with patch.object(module, 'reconstruct_claim', return_value=claim), \
             patch.object(module, 'analyze_visual_evidence', return_value={}), \
             patch.object(module, 'analyze_policy_and_evidence', return_value=batch) as combined, \
             patch.object(module, 'analyze_policy') as legacy_policy, \
             patch.object(module, 'analyze_evidence') as legacy_evidence, \
             patch.object(module, 'analyze_cross_modal_evidence', return_value={}), \
             patch.object(module, 'analyze_missing_information', return_value={'ready_for_adjudication': True}), \
             patch.object(module, 'adjudicate_claim', return_value={'recommendation': 'REVIEW'}), \
             patch.object(module, 'critique_adjudication', return_value={'verification_status': 'CHECKED'}) as critic:
            result = module.optimized_claim_graph.invoke({'claim_id': 'CLM-TEST', 'raw_documents': 'claim',
                'document_metadata': metadata, 'image_files': []})
        combined.assert_called_once()
        self.assertEqual(combined.call_args.kwargs['document_metadata'], metadata[1:])
        legacy_policy.assert_not_called()
        legacy_evidence.assert_not_called()
        critic.assert_called_once()
        self.assertEqual(result['evidence_analysis'], batch['evidence_analysis'])
        self.assertEqual(result['critic_feedback']['verification_status'], 'CHECKED')

    def test_compact_visual_prompt_keeps_aggregate_findings_and_original_state(self):
        visual = {'images_analyzed': ['photo.jpg'], 'visible_damage': [{'region': 'front_bumper'}],
                  'visual_confidence': 0.9, 'image_observations': [{'repeated': 'large narrative'}],
                  'regions_visible_intact': ['windscreen']}
        with patch.object(module, 'analyze_cross_modal_evidence', return_value={}) as analyze:
            module.compact_cross_modal_node({'claim_reconstruction': {}, 'evidence_analysis': {},
                                            'visual_analysis': visual})
        self.assertEqual(analyze.call_args.args[2], visual)
        self.assertTrue(analyze.call_args.kwargs['compact_prompt'])
        self.assertIn('image_observations', visual)

    def test_compaction_does_not_change_per_photo_quality_guard(self):
        clear = {'vehicle_visible': True, 'visual_confidence': .95, 'image_quality_issues': [],
                 'visible_damage': [{'region': 'front_bumper', 'confidence': .95}]}
        blurry = {'vehicle_visible': True, 'visual_confidence': .3,
                  'image_quality_issues': ['Blurred photograph'], 'visible_damage': []}
        visual = {'images_analyzed': ['clear.jpg', 'blur.jpg'], 'visual_confidence': .9,
                  'vehicle_visible': True, 'image_quality_issues': ['Blurred photograph'],
                  'visible_damage': clear['visible_damage'], 'image_observations': [clear, blurry]}
        response = {**no_visual_evidence_result(), 'cross_modal_status': 'STRONG_ALIGNMENT',
                    'supported_items': ['Front bumper']}
        with patch('app.agents.multimodal_evidence_agent.generate_text', return_value=json.dumps(response)) as generate:
            result = module.compact_cross_modal_node({'claim_reconstruction': {},
                'evidence_analysis': {}, 'visual_analysis': visual})['cross_modal_analysis']
        self.assertIn('Front bumper', result['supported_items'])
        self.assertNotIn('Front bumper', result['unverifiable_items'])
        self.assertNotIn('image_observations', generate.call_args.args[0])

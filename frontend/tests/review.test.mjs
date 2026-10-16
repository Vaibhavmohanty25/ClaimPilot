import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
after(() => server.close());
const { default: ClaimReview } = await server.ssrLoadModule('/src/pages/ClaimReview.jsx');
function review(claim) {
  return renderToStaticMarkup(React.createElement(MemoryRouter, {
    initialEntries: [{ pathname: '/claims/review', state: { claim } }],
  }, React.createElement(ClaimReview)));
}

test('review exposes documentary evidence contradictions to the adjuster', () => {
  const html = review({ evidence_analysis: {
    evidence_status: 'CONTRADICTORY', contradictions: ['Incident dates disagree'],
    supported_claim_items: ['Bumper repair supported by estimate'],
    unsupported_claim_items: ['Unsubstantiated door replacement'],
    missing_evidence: ['Need itemized workshop invoice'], risk_flags: ['Estimate exceeds claimed loss'],
  } });
  for (const finding of ['Incident dates disagree', 'Bumper repair supported by estimate',
    'Unsubstantiated door replacement', 'Need itemized workshop invoice', 'Estimate exceeds claimed loss']) {
    assert.ok(html.includes(finding), `Review hides evidence finding: ${finding}`);
  }
});

test('review exposes partial cross-modal support and contradictions', () => {
  const html = review({ cross_modal_analysis: {
    partially_supported_items: ['Bumper partially visible'],
    cross_modal_contradictions: ['Photograph conflicts with bonnet replacement'],
  } });
  assert.ok(html.includes('Bumper partially visible'));
  assert.ok(html.includes('Photograph conflicts with bonnet replacement'));
});

test('review without navigation state offers intake', () => {
  const html = review(undefined);
  assert.ok(html.includes('No claim loaded'));
  assert.ok(html.includes('Process a Claim'));
});

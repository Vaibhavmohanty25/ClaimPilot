import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
after(() => server.close());
const { default: ProcessingState } = await server.ssrLoadModule('/src/components/claims/ProcessingState.jsx');
const render = progress => renderToStaticMarkup(React.createElement(ProcessingState, { progress }));

test('queued claims expose server queue position and elapsed time accessibly', () => {
  const html = render({ status: 'queued', message: 'Waiting for an available slot', queue_position: 3, elapsed_seconds: 125 });
  assert.ok(html.includes('role="status"'));
  assert.ok(html.includes('Queue position: 3'));
  assert.ok(html.includes('2m 5s'));
  assert.ok(html.includes('Waiting for an available slot'));
});

test('provider waiting shows real stage and server explanation without invented percentages', () => {
  const html = render({ status: 'processing', stage: 'provider_wait', message: 'Waiting for the analysis service; retrying shortly.', elapsed_seconds: 80 });
  assert.ok(html.includes('Waiting for the analysis service'));
  assert.ok(html.includes('retrying shortly'));
  assert.ok(!html.includes('Queue position'));
  assert.ok(!html.includes('%'));
});

test('connection loss retains last known progress and explains automatic recovery', () => {
  const html = render({ status: 'processing', message: 'Reading claim documents', connection_lost: true, connection_message: 'Reconnecting to your existing claim…' });
  assert.ok(html.includes('Reading claim documents'));
  assert.ok(html.includes('Reconnecting to your existing claim'));
});

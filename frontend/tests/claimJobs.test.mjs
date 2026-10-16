import test from 'node:test';
import assert from 'node:assert/strict';
import { createClaimJobClient } from '../src/api/claimJobs.js';

function setup(responses, post) {
  const values = new Map();
  const storage = { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) };
  const calls = [];
  let sequence = 0;
  const api = {
    post: async (url, body, options) => { calls.push({ url, body, options }); return post ? post(options) : { data: { job_id: 'job-1', status: 'queued', queue_position: 2, elapsed_seconds: 0 } }; },
    get: async (url, options) => { calls.push({ url, options }); const next = responses.shift(); if (next instanceof Error) throw next; return { data: next }; },
  };
  const client = createClaimJobClient({ api, storage, pause: async () => {}, uuid: () => `key-${++sequence}` });
  return { client, storage, calls, values };
}
const file = () => new File(['claim evidence'], 'claim.txt', { type: 'text/plain', lastModified: 123 });
const done = { job_id: 'job-1', status: 'completed', result: { claim_id: 'result-1' } };

test('submits one evidence bundle and reports queued and actual processing stages before returning result', async () => {
  const { client, calls, values } = setup([{ job_id: 'job-1', status: 'processing', stage: 'documents', message: 'Reading documents', elapsed_seconds: 8 }, done]);
  const progress = [];
  assert.deepEqual(await client.process([file()], { onProgress: p => progress.push(p) }), { claim_id: 'result-1' });
  assert.equal(calls.filter(c => c.body).length, 1);
  assert.equal(calls[0].url, '/claims/jobs');
  assert.equal(calls[0].body.getAll('files').length, 1);
  assert.equal(calls[0].options.headers['Idempotency-Key'], 'key-1');
  assert.deepEqual(progress.map(p => p.status), ['queued', 'processing', 'completed']);
  assert.equal(values.size, 0);
});

test('transient polling failure keeps the accepted job and reconnects without resubmitting', async () => {
  const { client, calls } = setup([new Error('offline'), done]);
  const progress = [];
  await client.process([file()], { onProgress: p => progress.push(p) });
  assert.ok(progress.some(p => p.connection_lost));
  assert.equal(calls.filter(c => c.body).length, 1);
});

test('reload resumes stored job without re-uploading evidence', async () => {
  const { client, calls } = setup([done]);
  client.rememberJob('job-1');
  assert.equal(client.getActiveJob(), 'job-1');
  assert.deepEqual(await client.resume('job-1'), { claim_id: 'result-1' });
  assert.equal(calls[0].url, '/claims/jobs/job-1');
  assert.equal(calls.filter(c => c.body).length, 0);
  assert.equal(client.getActiveJob(), null);
});

test('failed jobs surface server explanation and clear active state', async () => {
  const { client, values } = setup([{ job_id: 'job-1', status: 'failed', error: { message: 'Unable to read this PDF', status_code: 422 } }]);
  await assert.rejects(client.process([file()]), /Unable to read this PDF/);
  assert.equal(values.size, 0);
});

test('expired or restarted jobs explain loss and clear stored job', async () => {
  const missing = Object.assign(new Error('404'), { response: { status: 404 } });
  const { client } = setup([missing]);
  client.rememberJob('job-1');
  await assert.rejects(client.resume('job-1'), /expired|restart/i);
  assert.equal(client.getActiveJob(), null);
});

test('abort stops polling and callbacks while keeping server job available to resume', async () => {
  const controller = new AbortController();
  const { client, calls } = setup([done]);
  await assert.rejects(client.process([file()], { signal: controller.signal, onProgress: () => controller.abort() }), { name: 'AbortError' });
  assert.equal(client.getActiveJob(), 'job-1');
  assert.equal(calls.length, 1);
});

test('uncertain submission retries reuse persisted key for same bundle and change it for changed files', async () => {
  let reject = true;
  const { client, calls } = setup([done], () => {
    if (reject) throw new Error('connection interrupted');
    return { data: { job_id: 'job-1', status: 'queued' } };
  });
  await assert.rejects(client.process([file()]));
  await assert.rejects(client.process([file()]));
  assert.equal(calls[0].options.headers['Idempotency-Key'], calls[1].options.headers['Idempotency-Key']);
  await assert.rejects(client.process([new File(['other'], 'other.txt')]));
  assert.notEqual(calls[1].options.headers['Idempotency-Key'], calls[2].options.headers['Idempotency-Key']);
  reject = false;
  await client.process([file()]);
});

test('reselecting the same files after reload preserves an uncertain upload identity', async () => {
  const { client, calls } = setup([], () => { throw new Error('offline'); });
  await assert.rejects(client.process([file()]));
  client.resetSubmission([file()]);
  await assert.rejects(client.process([file()]));
  assert.equal(calls[0].options.headers['Idempotency-Key'], calls[1].options.headers['Idempotency-Key']);
  client.resetSubmission([]);
  await assert.rejects(client.process([file()]));
  assert.notEqual(calls[1].options.headers['Idempotency-Key'], calls[2].options.headers['Idempotency-Key']);
});

test('cancellation during a polling request discards the late response and can resume later', async () => {
  const controller = new AbortController();
  const { client, calls } = setup([done]);
  const progress = [];
  client.rememberJob('job-1');
  const running = client.resume('job-1', { signal: controller.signal, onProgress: p => progress.push(p) });
  controller.abort();
  await assert.rejects(running, { name: 'AbortError' });
  assert.equal(progress.length, 0);
  assert.equal(calls.length, 1);
  assert.equal(client.getActiveJob(), 'job-1');
});

test('provider cooldown never delays progress polling for the whole provider wait', async () => {
  const waits = [];
  const client = createClaimJobClient({
    api: { get: async () => ({ data: done }) },
    pause: async ms => waits.push(ms),
  });
  await client.resume('job-1', { initial: { job_id: 'job-1', status: 'processing', stage: 'provider_wait', retry_after_seconds: 120 } });
  assert.deepEqual(waits, [2000]);
});

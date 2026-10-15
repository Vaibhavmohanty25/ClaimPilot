const ACTIVE_JOB = 'claimpilot.activeJob';
const SUBMISSION = 'claimpilot.submission';
const fingerprintFiles = files => JSON.stringify(files.map(f => [f.name, f.size, f.type, f.lastModified]));

function checkAbort(signal) {
  if (signal?.aborted) throw new DOMException('Polling stopped', 'AbortError');
}

function pause(ms, signal) {
  return new Promise((resolve, reject) => {
    checkAbort(signal);
    const stop = () => { clearTimeout(timer); reject(new DOMException('Polling stopped', 'AbortError')); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', stop); resolve(); }, ms);
    signal?.addEventListener('abort', stop, { once: true });
  });
}

export function createClaimJobClient({ api, storage, pause: wait = pause, uuid = () => crypto.randomUUID(), pollInterval = 2000 }) {
  // Only job identity and submission identity are stored, never evidence or results.
  const get = key => storage?.getItem(key) ?? null;
  const set = (key, value) => storage?.setItem(key, value);
  const remove = key => storage?.removeItem(key);
  const clear = () => { remove(ACTIVE_JOB); remove(SUBMISSION); };
  const rememberJob = id => set(ACTIVE_JOB, id);

  async function resume(jobId, { signal, onProgress = () => {}, initial } = {}) {
    let latest = initial || { job_id: jobId, status: 'queued', message: 'Checking your claim’s progress…' };
    let next = initial;
    while (true) {
      checkAbort(signal);
      try {
        const job = next || (await api.get(`/claims/jobs/${encodeURIComponent(jobId)}`, { signal, timeout: 25000 })).data;
        checkAbort(signal);
        next = null;
        latest = job;
        onProgress(job);
        checkAbort(signal);
        if (job.status === 'completed') { clear(); return job.result; }
        if (job.status === 'failed') {
          clear();
          const error = new Error(job.error?.message || 'The claim could not be processed. Please try again.');
          error.terminal = true;
          throw error;
        }
      } catch (error) {
        checkAbort(signal);
        if (error.terminal) throw error;
        const status = error.response?.status;
        if (status === 404) {
          clear();
          throw new Error('This claim’s processing session expired or the service restarted. Please upload your evidence again.');
        }
        if (status && status < 500 && status !== 429) throw error;
        onProgress({ ...latest, connection_lost: true, connection_message: 'Connection interrupted. Reconnecting to your existing claim…' });
      }
      checkAbort(signal);
      await wait(pollInterval, signal);
    }
  }

  async function process(files, options = {}) {
    checkAbort(options.signal);
    const active = get(ACTIVE_JOB);
    if (active) return resume(active, options);
    const fingerprint = fingerprintFiles(files);
    let pending;
    try { pending = JSON.parse(get(SUBMISSION)); } catch { /* Replace invalid session data. */ }
    if (pending?.fingerprint !== fingerprint) pending = { fingerprint, key: uuid() };
    set(SUBMISSION, JSON.stringify(pending));
    const body = new FormData();
    files.forEach(file => body.append('files', file));
    const response = await api.post('/claims/jobs', body, {
      signal: options.signal, timeout: 25000, headers: { 'Idempotency-Key': pending.key },
    });
    rememberJob(response.data.job_id);
    return resume(response.data.job_id, { ...options, initial: response.data });
  }

  function resetSubmission(files) {
    let pending;
    try { pending = JSON.parse(get(SUBMISSION)); } catch { /* Remove invalid data. */ }
    if (!files || pending?.fingerprint !== fingerprintFiles(files)) remove(SUBMISSION);
  }

  return { process, resume, rememberJob, getActiveJob: () => get(ACTIVE_JOB), resetSubmission };
}

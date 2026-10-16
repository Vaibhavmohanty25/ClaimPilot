"""Bounded, ephemeral single-worker claim queue for one application process."""
import asyncio
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException
from app.services.job_progress import progress_scope


@dataclass(frozen=True)
class SavedUpload:
    filename: str
    path: Path


def cleanup_uploads(files):
    for uploaded in files:
        uploaded.path.unlink(missing_ok=True)


class ClaimJobQueue:
    def __init__(self, processor, *, max_waiting=5, retention_seconds=3600,
                 max_completed=100, clock=monotonic):
        self.processor = processor
        self.max_waiting = max_waiting
        self.retention_seconds = retention_seconds
        self.max_completed = max_completed
        self.clock = clock
        self.processing_lock = asyncio.Lock()
        self._jobs = {}
        self._keys = {}
        self._pending = deque()
        self._wake = asyncio.Event()
        self._worker = None
        self._closed = False

    def _prune(self):
        completed = sorted((job for job in self._jobs.values() if job.get('finished') is not None),
                           key=lambda job: job['finished'])
        remove_count = max(0, len(completed) - self.max_completed)
        for index, job in enumerate(completed):
            if index < remove_count or self.clock() - job['finished'] >= self.retention_seconds:
                self._jobs.pop(job['job_id'], None)
                if job.get('key'):
                    self._keys.pop(job['key'], None)

    def _receipt(self, job):
        receipt = {key: job[key] for key in ('job_id', 'status', 'stage', 'message')}
        receipt['queue_position'] = (list(self._pending).index(job['job_id']) + 1
                                     if job['job_id'] in self._pending else 0)
        receipt['elapsed_seconds'] = round(max(0, job.get('finished', self.clock()) - job['created']), 1)
        if job['status'] == 'completed':
            receipt['result'] = job['result']
        elif job['status'] == 'failed':
            receipt['error'] = job['error']
        if job.get('retry_after_seconds') is not None:
            receipt['retry_after_seconds'] = job['retry_after_seconds']
        return receipt

    def get(self, job_id):
        self._prune()
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(404, 'Claim job was not found. Jobs expire after one hour and are lost on server restart. Submit the documents again.')
        return self._receipt(job)

    async def submit(self, files, fingerprint, idempotency_key=None):
        # Admission has no awaits: duplicate lookup, capacity check and insertion
        # are atomic with respect to concurrent requests on this event loop.
        admitted = False
        try:
            self._prune()
            if self._closed:
                raise HTTPException(503, 'Claim processing is shutting down. Try again shortly.')
            if idempotency_key:
                existing_id = self._keys.get(idempotency_key)
                if existing_id:
                    job = self._jobs[existing_id]
                    if job['fingerprint'] != fingerprint:
                        raise HTTPException(409, 'Idempotency-Key was already used for different documents.')
                    return self._receipt(job)
            if len(self._pending) >= self.max_waiting:
                raise HTTPException(503, 'The claim queue is full. Try again after a queued claim finishes.', headers={'Retry-After': '10'})
            job_id = str(uuid4())
            job = dict(job_id=job_id, status='queued', stage='queued',
                       message='Waiting for the previous claim to finish.', created=self.clock(),
                       files=files, fingerprint=fingerprint, key=idempotency_key)
            self._jobs[job_id] = job
            self._pending.append(job_id)
            if idempotency_key:
                self._keys[idempotency_key] = job_id
            admitted = True
            self._wake.set()
            if self._worker is None or self._worker.done():
                self._worker = asyncio.create_task(self._run(), name='claimpilot-claim-queue')
            return self._receipt(job)
        finally:
            if not admitted:
                cleanup_uploads(files)

    def _progress(self, job, stage, message=None, retry_after_seconds=None):
        if job["status"] != "processing":
            return
        job.update(stage=stage, message=message or stage.replace('_', ' ').capitalize())
        job['retry_after_seconds'] = retry_after_seconds

    async def _run(self):
        while not self._closed:
            await self._wake.wait()
            self._wake.clear()
            while self._pending and not self._closed:
                job = self._jobs[self._pending[0]]
                try:
                    async with self.processing_lock:
                        self._pending.popleft()
                        job.update(status='processing', stage='extracting', message='Reading claim documents.')
                        loop = asyncio.get_running_loop()
                        def progress(stage, message, retry_after_seconds, current_job=job):
                            loop.call_soon_threadsafe(self._progress, current_job, stage, message, retry_after_seconds)
                        with progress_scope(progress):
                            job['result'] = await self.processor(job['files'])
                        job.update(status='completed', stage='completed', message='Claim assessment is ready.')
                except asyncio.CancelledError:
                    job.update(status='failed', stage='failed', message='Claim processing stopped.',
                               error={'message': 'Server stopped processing this claim. Submit the documents again.', 'status_code': 503})
                    raise
                except Exception as error:
                    status = error.status_code if isinstance(error, HTTPException) else 500
                    # HTTPException details originate in our sanitized processor;
                    # unexpected errors never expose raw provider or file details.
                    message = str(error.detail) if isinstance(error, HTTPException) else 'Claim processing failed. Please try again.'
                    job.update(status='failed', stage='failed', message='Claim processing failed.',
                               error={'message': message, 'status_code': status})
                finally:
                    job['finished'] = self.clock()
                    job.pop('retry_after_seconds', None)
                    cleanup_uploads(job.pop('files', []))
                    self._prune()

    async def shutdown(self):
        self._closed = True
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
        for job in self._jobs.values():
            cleanup_uploads(job.pop('files', []))
            if job['status'] in ('queued', 'processing'):
                job.update(status='failed', stage='failed', message='Claim processing stopped.', finished=self.clock(),
                           error={'message': 'Server stopped processing this claim. Submit the documents again.', 'status_code': 503})
        self._pending.clear()

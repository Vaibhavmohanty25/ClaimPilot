"""Queue contract regressions; no provider or network work."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from fastapi import HTTPException
from app.services.claim_jobs import ClaimJobQueue, SavedUpload
from app.services.job_progress import report_progress


class ClaimQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.queues = []

    async def asyncTearDown(self):
        for queue in self.queues:
            await queue.shutdown()
        self.directory.cleanup()

    def upload(self, name='claim.txt', content=b'claim'):
        path = Path(self.directory.name) / str(len(list(Path(self.directory.name).iterdir())))
        path.write_bytes(content)
        return SavedUpload(name, path)

    def queue(self, processor, **options):
        queue = ClaimJobQueue(processor, **options)
        self.queues.append(queue)
        return queue

    async def settle(self, queue, job_id):
        for _ in range(100):
            receipt = queue.get(job_id)
            if receipt['status'] in ('completed', 'failed'):
                return receipt
            await asyncio.sleep(.001)
        self.fail('Worker did not finish')

    async def test_returns_before_processing_and_runs_fifo_with_positions(self):
        entered, release = asyncio.Event(), asyncio.Event()
        order = []
        async def process(files):
            order.append(files[0].filename)
            entered.set()
            await release.wait()
            return {'ok': True}
        queue = self.queue(process)
        first_file = self.upload('first.txt')
        first = await queue.submit([first_file], 'one')
        self.assertEqual(first['status'], 'queued')
        await entered.wait()
        second = await queue.submit([self.upload('second.txt')], 'two')
        third = await queue.submit([self.upload('third.txt')], 'three')
        self.assertEqual(queue.get(second['job_id'])['queue_position'], 1)
        self.assertEqual(queue.get(third['job_id'])['queue_position'], 2)
        self.assertEqual(order, ['first.txt'])
        release.set()
        self.assertEqual((await self.settle(queue, third['job_id']))['result'], {'ok': True})
        self.assertEqual(order, ['first.txt', 'second.txt', 'third.txt'])
        self.assertFalse(first_file.path.exists())

    async def test_idempotency_is_atomic_and_rejects_conflicting_content(self):
        release = asyncio.Event()
        async def process(files):
            await release.wait()
            return {}
        queue = self.queue(process)
        files = [[self.upload()], [self.upload()]]
        one, two = await asyncio.gather(*(queue.submit(item, 'digest', 'key') for item in files))
        self.assertEqual(one['job_id'], two['job_id'])
        self.assertFalse(files[1][0].path.exists())
        conflicting = self.upload()
        with self.assertRaises(HTTPException) as caught:
            await queue.submit([conflicting], 'other-digest', 'key')
        self.assertEqual(caught.exception.status_code, 409)
        self.assertFalse(conflicting.path.exists())
        self.assertNotIn('key', one)
        release.set()

    async def test_failure_is_sanitized_and_worker_continues(self):
        calls = 0
        async def process(files):
            nonlocal calls
            calls += 1
            report_progress('extracting', 'Reading documents')
            if calls == 1:
                raise RuntimeError('secret-token /private/path')
            return {'claim_id': 'CLM-123'}
        queue = self.queue(process)
        bad_file = self.upload()
        bad = await queue.submit([bad_file], 'one')
        good = await queue.submit([self.upload()], 'two')
        failure = await self.settle(queue, bad['job_id'])
        self.assertEqual(failure['status'], 'failed')
        self.assertNotIn('secret', str(failure))
        self.assertNotIn('result', failure)
        self.assertFalse(bad_file.path.exists())
        self.assertEqual((await self.settle(queue, good['job_id']))['status'], 'completed')

    async def test_queue_limit_and_shutdown_clean_all_uploads(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def process(files):
            entered.set()
            await release.wait()
        queue = self.queue(process, max_waiting=1)
        active = self.upload()
        await queue.submit([active], 'one')
        await entered.wait()
        waiting = self.upload()
        await queue.submit([waiting], 'two')
        rejected = self.upload()
        with self.assertRaises(HTTPException) as caught:
            await queue.submit([rejected], 'three')
        self.assertEqual(caught.exception.status_code, 503)
        self.assertFalse(rejected.path.exists())
        await queue.shutdown()
        self.assertFalse(active.path.exists())
        self.assertFalse(waiting.path.exists())

    async def test_expiry_and_retention_remove_ids_and_idempotency_mapping(self):
        clock = [0.0]
        async def process(files):
            return {}
        queue = self.queue(process, retention_seconds=10, max_completed=1, clock=lambda: clock[0])
        first = await queue.submit([self.upload()], 'one', 'key')
        await self.settle(queue, first['job_id'])
        second = await queue.submit([self.upload()], 'two')
        await self.settle(queue, second['job_id'])
        with self.assertRaises(HTTPException) as caught:
            queue.get(first['job_id'])
        self.assertEqual(caught.exception.status_code, 404)
        clock[0] = 11
        with self.assertRaises(HTTPException):
            queue.get(second['job_id'])
        retry = await queue.submit([self.upload()], 'one', 'key')
        self.assertNotEqual(retry['job_id'], first['job_id'])

class ClaimJobApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app import main
        self.main = main
        self.directory = tempfile.TemporaryDirectory()
        from unittest.mock import patch
        self.upload_patch = patch.object(main, 'UPLOAD_DIR', Path(self.directory.name))
        self.upload_patch.start()
        import httpx
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test')

    async def asyncTearDown(self):
        await self.main._get_job_queue().shutdown()
        await self.client.aclose()
        self.upload_patch.stop()
        self.directory.cleanup()

    async def test_post_returns_202_before_graph_finishes_and_poll_reports_result(self):
        import threading
        from unittest.mock import patch
        entered, release = threading.Event(), threading.Event()
        def graph(state):
            entered.set()
            release.wait(2)
            return {'claim_reconstruction': {'incident': 'collision'}}
        with patch.object(self.main, '_queued_graph_invoke', side_effect=graph):
            response = await self.client.post('/claims/jobs', files={'files': ('claim.txt', b'collision report', 'text/plain')})
            self.assertEqual(response.status_code, 202)
            receipt = response.json()
            self.assertEqual(receipt['status'], 'queued')
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(.001)
            self.assertTrue(entered.is_set())
            poll = await self.client.get('/claims/jobs/' + receipt['job_id'])
            self.assertEqual(poll.json()['status'], 'processing')
            release.set()
            final = await ClaimQueueTests.settle(self, self.main._get_job_queue(), receipt['job_id'])
            self.assertEqual(final['result']['reconstruction'], {'incident': 'collision'})
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_bad_type_file_count_and_size_are_rejected_without_saved_uploads(self):
        from unittest.mock import patch
        unsupported = await self.client.post('/claims/jobs', files={'files': ('run.exe', b'bad', 'application/octet-stream')})
        self.assertEqual(unsupported.status_code, 400)
        too_many = await self.client.post('/claims/jobs', files=[('files', ('claim.txt', b'claim'))] * 11)
        self.assertEqual(too_many.status_code, 400)
        with patch.object(self.main, 'MAX_FILE_BYTES', 8), patch.object(self.main, 'MAX_TOTAL_BYTES', 10):
            too_large = await self.client.post('/claims/jobs', files={'files': ('claim.txt', b'x' * 9)})
            self.assertEqual(too_large.status_code, 413)
            total = await self.client.post('/claims/jobs', files=[('files', ('a.txt', b'x' * 6)), ('files', ('b.txt', b'x' * 6))])
            self.assertEqual(total.status_code, 413)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    async def test_synchronous_endpoint_shares_queue_processing_lock(self):
        import threading
        from unittest.mock import patch
        entered, release = threading.Event(), threading.Event()
        active = 0
        peak = 0
        def graph(state):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            entered.set()
            release.wait(2)
            active -= 1
            return {}
        with patch.object(self.main, '_queued_graph_invoke', side_effect=graph), patch.object(self.main.claim_graph, 'invoke', side_effect=graph):
            receipt = (await self.client.post('/claims/jobs', files={'files': ('q.txt', b'claim')})).json()
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(.001)
            legacy = asyncio.create_task(self.client.post('/claims/process', files={'files': ('sync.txt', b'claim')}))
            await asyncio.sleep(.01)
            self.assertFalse(legacy.done())
            release.set()
            self.assertEqual((await legacy).status_code, 200)
            await ClaimQueueTests.settle(self, self.main._get_job_queue(), receipt['job_id'])
            self.assertEqual(peak, 1)

class JobProgressTests(unittest.TestCase):
    def test_observed_node_reports_before_entering_node(self):
        from app.services.observability import observed_node
        from app.services.job_progress import progress_scope
        events = []
        @observed_node
        def reconstruction_node(state):
            self.assertEqual(events[0][0], 'reconstruction_node')
            return {}
        with progress_scope(lambda *event: events.append(event)):
            reconstruction_node({'claim_id': 'CLM-123'})
        self.assertEqual(len(events), 1)
        self.assertIn('Reconstruct', events[0][1])

    def test_provider_retry_reports_wait_without_provider_exception_text(self):
        import httpx
        from groq import RateLimitError
        from types import SimpleNamespace
        from unittest.mock import patch
        from app.services.job_progress import progress_scope
        from app.services.provider_retry import request_with_retry
        error = RateLimitError('secret body', response=httpx.Response(429, request=httpx.Request('POST', 'https://example.com')), body={})
        good = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
        outcomes = iter([error, good])
        def operation():
            result = next(outcomes)
            if isinstance(result, Exception):
                raise result
            return result
        events = []
        with patch('time.sleep'), progress_scope(lambda *event: events.append(event)):
            self.assertEqual(request_with_retry(operation, model='test', stage='text_llm'), '{}')
        self.assertEqual(events[0][0], 'provider_wait')
        self.assertEqual(events[0][2], 1)
        self.assertNotIn('secret', str(events))

class ClaimLifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_runs_even_when_lifespan_body_raises(self):
        from app import main
        calls = []
        class Queue:
            async def shutdown(self):
                calls.append('shutdown')
        from unittest.mock import patch
        with patch.object(main.app.state, 'claim_jobs', Queue(), create=True):
            with self.assertRaises(ValueError):
                async with main.lifespan(main.app):
                    raise ValueError('server lifecycle failed')
        self.assertEqual(calls, ['shutdown'])

class ClaimThreadSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_thread_progress_reaches_poll_and_shutdown_waits_before_cleanup(self):
        import threading
        from unittest.mock import patch
        from app import main
        from app.services.observability import observed_node
        entered, release = threading.Event(), threading.Event()
        @observed_node
        def reconstruction_node(state):
            entered.set()
            release.wait(2)
            return {}
        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'UPLOAD_DIR', Path(directory)), patch.object(main, '_queued_graph_invoke', side_effect=reconstruction_node):
            from tests.test_api_multimodal import FakeUpload
            receipt = await main.create_claim_job([FakeUpload('claim.txt', b'collision')], None)
            queue = main._get_job_queue()
            for _ in range(100):
                if entered.is_set() and queue.get(receipt['job_id'])['stage'] == 'reconstruction_node':
                    break
                await asyncio.sleep(.001)
            self.assertEqual(queue.get(receipt['job_id'])['stage'], 'reconstruction_node')
            shutdown = asyncio.create_task(queue.shutdown())
            await asyncio.sleep(.01)
            self.assertFalse(shutdown.done())
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            release.set()
            await shutdown
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertEqual(queue.get(receipt['job_id'])['status'], 'failed')

    async def test_http_retry_uses_saved_content_fingerprint_and_cleans_duplicates(self):
        import httpx
        from app import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'UPLOAD_DIR', Path(directory)), patch.object(main, '_queued_graph_invoke', return_value={}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
                args = dict(headers={'Idempotency-Key': 'same-key'}, files={'files': ('claim.txt', b'collision')})
                first = await client.post('/claims/jobs', **args)
                second = await client.post('/claims/jobs', **args)
                self.assertEqual(first.status_code, 202)
                self.assertEqual(first.json()['job_id'], second.json()['job_id'])
                conflict = await client.post('/claims/jobs', headers={'Idempotency-Key': 'same-key'}, files={'files': ('claim.txt', b'different')})
                self.assertEqual(conflict.status_code, 409)
                await ClaimQueueTests.settle(self, main._get_job_queue(), first.json()['job_id'])
                self.assertEqual(list(Path(directory).iterdir()), [])
                await main._get_job_queue().shutdown()

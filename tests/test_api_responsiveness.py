"""Regression: a slow claim must not prevent the server handling other work."""
import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main
from tests.test_api_multimodal import FakeUpload


class ApiResponsivenessTests(unittest.TestCase):
    def test_slow_graph_does_not_block_the_request_event_loop(self):
        def slow_graph(state):
            time.sleep(0.2)
            return {}

        async def exercise():
            processing = asyncio.create_task(main.process_claim([FakeUpload('claim.txt', b'Collision report')]))
            await asyncio.sleep(0.02)
            blocked_until_complete = processing.done()
            await processing
            return blocked_until_complete

        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'UPLOAD_DIR', Path(directory)), patch.object(main.claim_graph, 'invoke', side_effect=slow_graph):
            self.assertFalse(asyncio.run(exercise()), 'Claim graph blocked unrelated async server work until it finished.')


    def test_concurrent_claims_use_one_document_worker(self):
        import threading
        worker_threads = set()
        active = 0
        peak = 0
        lock = threading.Lock()

        def load(path):
            nonlocal active, peak
            with lock:
                worker_threads.add(threading.get_ident())
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.1)
                return {"text": "Motor collision report", "file_type": "text", "extraction_method": "native_text"}
            finally:
                with lock:
                    active -= 1

        async def exercise():
            return await asyncio.gather(*(main.process_claim([FakeUpload(f'claim{i}.txt', b'claim')]) for i in range(2)))

        with tempfile.TemporaryDirectory() as directory, patch.object(main, 'UPLOAD_DIR', Path(directory)), patch.object(main, 'load_document', side_effect=load), patch.object(main.claim_graph, 'invoke', return_value={}):
            responses = asyncio.run(exercise())
        self.assertEqual(len(responses), 2)
        self.assertEqual(peak, 1, 'PDF/OCR extraction must not overlap across claims.')
        self.assertEqual(len(worker_threads), 1, 'Document libraries must run on one dedicated thread.')


if __name__ == '__main__':
    unittest.main()

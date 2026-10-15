"""Build preparation orchestration without loading models or making requests."""
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from scripts import prepare_runtime


class RuntimePreparationTests(unittest.TestCase):
    def test_parent_runs_isolated_stages_and_stops_after_failure(self):
        with patch.object(prepare_runtime.subprocess, "run") as run:
            prepare_runtime.main([])
        self.assertEqual(
            [call.args[0][-1] for call in run.call_args_list],
            ["embeddings", "ocr", "policy"],
        )
        for call in run.call_args_list:
            self.assertEqual(call.args[0][:3], [sys.executable, "-m", "scripts.prepare_runtime"])
            self.assertEqual(call.kwargs, {"cwd": prepare_runtime.ROOT, "check": True})

        failure = subprocess.CalledProcessError(1, "prepare OCR")
        with patch.object(prepare_runtime.subprocess, "run", side_effect=[None, failure]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                prepare_runtime.main([])
        self.assertEqual(run.call_count, 2)

    def test_policy_seed_closes_store_on_success_and_error(self):
        for failure in (None, RuntimeError("seed failed")):
            with self.subTest(failure=failure):
                ingest = ModuleType("app.rag.ingest")
                ingest.ingest_policy = Mock(return_value=8, side_effect=failure)
                store = ModuleType("app.rag.qdrant_store")
                store.qdrant_client = Mock()
                with patch.dict(sys.modules, {"app.rag.ingest": ingest, "app.rag.qdrant_store": store}):
                    if failure:
                        with self.assertRaises(RuntimeError):
                            prepare_runtime.prepare_policy()
                    else:
                        prepare_runtime.prepare_policy()
                store.qdrant_client.close.assert_called_once()
                ingest.ingest_policy.assert_called_once_with("data/policies/motor_policy.txt")

    def test_embedding_stage_warms_existing_embedding_model(self):
        module = ModuleType("app.rag.embeddings")
        module.embed_text = Mock(return_value=[0.0] * 384)
        with patch.dict(sys.modules, {"app.rag.embeddings": module}):
            prepare_runtime.prepare_embeddings()
        module.embed_text.assert_called_once_with("insurance policy")

    def test_ocr_stage_initializes_existing_reader(self):
        module = ModuleType("app.services.ocr_service")
        module.get_reader = Mock()
        with patch.dict(sys.modules, {"app.services.ocr_service": module}):
            prepare_runtime.prepare_ocr()
        module.get_reader.assert_called_once()


if __name__ == "__main__":
    unittest.main()

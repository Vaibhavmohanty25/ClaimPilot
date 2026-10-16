import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qdrant_client import QdrantClient

from app.rag import ingest, retriever


class PolicyIndexTests(unittest.TestCase):
    def setUp(self):
        self.client = QdrantClient(":memory:")
        self.addCleanup(self.client.close)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        # Only embedding inference is substituted; storage, filters, and
        # similarity queries use the actual local Qdrant implementation.
        for module in (ingest, retriever):
            client_patch = patch.object(module, "qdrant_client", self.client)
            client_patch.start()
            self.addCleanup(client_patch.stop)
            embed_patch = patch.object(module, "embed_text", return_value=[1.0, 0.0, 0.0])
            embed_patch.start()
            self.addCleanup(embed_patch.stop)

    def policy_file(self, name, content):
        path = Path(self.directory.name) / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def all_sections(self):
        return self.client.scroll(collection_name=ingest.COLLECTION_NAME, limit=100)[0]

    def test_reingesting_shorter_policy_removes_outdated_sections(self):
        path = self.policy_file("policy.txt", "SECTION 1 - COVER\nAccidents covered\nSECTION 2 - OLD\nOld deductible")
        ingest.ingest_policy(path)
        Path(path).write_text("SECTION 1 - COVER\nUpdated coverage", encoding="utf-8")
        ingest.ingest_policy(path)
        self.assertEqual([point.payload["text"] for point in self.all_sections()], ["SECTION 1 - COVER\nUpdated coverage"])

    def test_ingesting_second_policy_replaces_active_policy(self):
        first = self.policy_file("first.txt", "SECTION 1 - FIRST\nFirst policy")
        second = self.policy_file("second.txt", "SECTION 1 - SECOND\nSecond policy")
        ingest.ingest_policy(first)
        ingest.ingest_policy(second)
        self.assertEqual({point.payload["source"] for point in self.all_sections()}, {second})

    def test_invalid_policy_is_rejected_before_modifying_index(self):
        path = self.policy_file("policy.txt", "SECTION 1 - COVER\nAccidents covered")
        ingest.ingest_policy(path)
        Path(path).write_text("No policy section headers", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest.ingest_policy(path)
        self.assertEqual(len(self.all_sections()), 1)

    def test_retriever_explains_missing_policy_collection(self):
        with self.assertRaisesRegex(RuntimeError, "app.rag.ingest"):
            retriever.retrieve_policy_context("collision")

    def test_ingested_policy_is_retrievable_with_sources(self):
        path = self.policy_file("policy.txt", "SECTION 1 - COLLISION\nAccidental collision is covered")
        ingest.ingest_policy(path)
        result = retriever.retrieve_policy_context("collision", limit=1)
        self.assertEqual(len(result), 1)
        self.assertIn("Accidental collision is covered", result[0]["text"])
        self.assertEqual(result[0]["source"], path)
        self.assertAlmostEqual(result[0]["score"], 1.0)

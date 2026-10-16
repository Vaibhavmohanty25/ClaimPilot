"""Prevent accidental Groq calls in offline discovery, even with a live .env."""
import os
import sys
from unittest.mock import patch

LIVE_REQUESTED = "tests.test_live_multimodal" in sys.argv and os.getenv("RUN_LIVE_MULTIMODAL_TESTS") == "1"
if not LIVE_REQUESTED:
    # A dummy key permits client construction; the guard below forbids network calls.
    os.environ.setdefault("GROQ_API_KEY", "offline-test-key")
    _provider_guard = patch("groq.resources.chat.completions.Completions.create",
                            side_effect=AssertionError("Live Groq requests are forbidden in offline tests."))
    _provider_guard.start()

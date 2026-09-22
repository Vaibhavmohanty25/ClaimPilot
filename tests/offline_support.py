"""Prevent accidental Groq calls in offline discovery, even with a live .env."""
import os
import sys
from unittest.mock import patch

LIVE_REQUESTED = "tests.test_live_multimodal" in sys.argv and os.getenv("RUN_LIVE_MULTIMODAL_TESTS") == "1"
if not LIVE_REQUESTED:
    _provider_guard = patch("groq.resources.chat.completions.Completions.create",
                            side_effect=AssertionError("Live Groq requests are forbidden in offline tests."))
    _provider_guard.start()

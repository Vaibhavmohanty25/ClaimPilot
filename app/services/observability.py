"""Allowlisted JSON events; never serialize state or exceptions."""
import json
import logging
import re
from contextvars import ContextVar
from functools import wraps
from time import perf_counter
from app.services.privacy import public_response

claim_context = ContextVar("claim_id", default=None)
logger = logging.getLogger("claimpilot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


def log_event(stage, success, **fields):
    event = {"stage": stage, "success": success, "claim_id": fields.get("claim_id", claim_context.get())}
    for key in ("duration_ms", "retry_count", "model", "image_count", "extraction_method", "error_code"):
        if key in fields:
            event[key] = fields[key]
    if event["claim_id"] and not re.fullmatch(r"CLM-[A-Za-z0-9-]{1,40}", str(event["claim_id"])):
        event["claim_id"] = None
    logger.info(json.dumps(public_response(event)))


def observed_node(function):
    @wraps(function)
    def wrapped(state):
        token = claim_context.set(state.get("claim_id"))
        start = perf_counter()
        success = False
        try:
            result = function(state)
            success = True
            return result
        finally:
            log_event(function.__name__, success, duration_ms=round((perf_counter() - start) * 1000, 2),
                      image_count=len(state.get("image_files", [])))
            claim_context.reset(token)
    return wrapped

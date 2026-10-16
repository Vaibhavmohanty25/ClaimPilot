"""Request-local progress notifications, propagated into provider worker threads."""
from contextlib import contextmanager
from contextvars import ContextVar

_progress_callback = ContextVar('claim_progress_callback', default=None)


def report_progress(stage, message=None, retry_after_seconds=None):
    callback = _progress_callback.get()
    if callback is not None:
        callback(stage, message, retry_after_seconds)


@contextmanager
def progress_scope(callback):
    token = _progress_callback.set(callback)
    try:
        yield
    finally:
        _progress_callback.reset(token)

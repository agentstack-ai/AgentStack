"""Conversation context shared by web search and page fetching."""

from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4


_session_id: ContextVar[str | None] = ContextVar('agentstack_search_session', default=None)


@contextmanager
def search_session():
    """Start a research run; related tool calls share an opaque conversation ID.

    The CLI starts a session for each ``agentstack run``. Applications using the
    tools directly can wrap their conversation in this context manager instead.
    Nested sessions represent new conversations and restore the outer context.
    """
    token = _session_id.set(str(uuid4()))
    try:
        yield
    finally:
        _session_id.reset(token)


def get_search_session_id() -> str:
    """Use the current conversation, or a new ID for a standalone tool call."""
    return _session_id.get() or str(uuid4())

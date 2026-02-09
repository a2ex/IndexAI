"""Shared test fixtures and helpers for verification tasks tests."""
import uuid
import types
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.url import URLStatus


PATCHES_BASE = "app.tasks.verification_tasks"


def make_url(status=URLStatus.submitted, url="https://example.com/page", **overrides):
    """Create a fake URL object with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "url": url,
        "status": status,
        "check_count": 0,
        "is_indexed": False,
        "last_checked_at": None,
        "check_method": None,
        "indexed_at": None,
        "indexed_title": None,
        "indexed_snippet": None,
        "submitted_at": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def make_mock_db(urls):
    """Create a mock async DB session that returns the given URLs from queries."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = urls
    result.scalars.return_value.first.return_value = urls[0] if urls else None
    db.execute = AsyncMock(return_value=result)
    return db


def make_session_factory(db):
    """Create a mock session factory that yields the given db as async context manager."""
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx
    return factory


def make_checker(is_indexed, method="gsc_inspection", title=None, snippet=None):
    """Create a mock IndexationChecker returning a fixed result."""
    result = {"is_indexed": is_indexed, "method": method}
    if title is not None:
        result["title"] = title
    if snippet is not None:
        result["snippet"] = snippet
    checker = AsyncMock()
    checker.check_url = AsyncMock(return_value=result)
    return checker

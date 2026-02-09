"""Tests for verification_tasks.py — URL indexation checking logic."""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.url import URLStatus
from tests.conftest import (
    PATCHES_BASE,
    make_url,
    make_mock_db,
    make_session_factory,
    make_checker,
)


# ---------------------------------------------------------------------------
# _check_urls
# ---------------------------------------------------------------------------
class TestCheckUrls:

    async def test_no_urls_to_check(self):
        db = make_mock_db([])
        factory = make_session_factory(db)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker") as MockChecker:
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)
            MockChecker.assert_not_called()

    async def test_url_becomes_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, title="Test Page", snippet="Test snippet")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.status == URLStatus.indexed
        assert url_obj.is_indexed is True
        assert url_obj.indexed_title == "Test Page"
        assert url_obj.indexed_snippet == "Test snippet"
        assert url_obj.check_count == 1
        assert url_obj.check_method == "gsc_inspection"
        mock_notify.assert_awaited_once()
        db.commit.assert_awaited()

    async def test_url_becomes_not_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.status == URLStatus.not_indexed
        assert url_obj.check_count == 1
        mock_notify.assert_not_awaited()
        db.commit.assert_awaited()

    async def test_inconclusive_check_keeps_status(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(None, method="fallback")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.status == URLStatus.indexing
        mock_notify.assert_not_awaited()

    async def test_submitted_transitions_to_indexing_before_check(self):
        url_obj = make_url(status=URLStatus.submitted)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        statuses_during_check = []

        async def spy_check(url):
            statuses_during_check.append(url_obj.status)
            return {"is_indexed": False, "method": "gsc_inspection"}

        checker = AsyncMock()
        checker.check_url = spy_check

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert statuses_during_check == [URLStatus.indexing]
        assert url_obj.status == URLStatus.not_indexed

    async def test_exception_triggers_rollback(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        checker = AsyncMock()
        checker.check_url = AsyncMock(side_effect=Exception("API error"))

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        db.rollback.assert_awaited()

    async def test_multiple_urls_one_fails_other_succeeds(self):
        url1 = make_url(status=URLStatus.indexing, url="https://example.com/1")
        url2 = make_url(status=URLStatus.indexing, url="https://example.com/2")
        db = make_mock_db([url1, url2])
        factory = make_session_factory(db)

        call_count = 0

        async def mock_check(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First URL fails")
            return {"is_indexed": True, "method": "gsc", "title": "OK", "snippet": "ok"}

        checker = AsyncMock()
        checker.check_url = mock_check

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url2.status == URLStatus.indexed


# ---------------------------------------------------------------------------
# _check_single_url
# ---------------------------------------------------------------------------
class TestCheckSingleUrl:

    async def test_url_not_found_returns_early(self):
        db = make_mock_db([])
        factory = make_session_factory(db)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker") as MockChecker:
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(uuid.uuid4()))
            MockChecker.assert_not_called()

    async def test_single_url_becomes_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, method="custom_search", title="Found", snippet="Found snippet")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(url_obj.id))

        assert url_obj.status == URLStatus.indexed
        assert url_obj.is_indexed is True
        assert url_obj.indexed_title == "Found"
        mock_notify.assert_awaited_once()
        db.commit.assert_awaited()

    async def test_single_url_becomes_not_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(url_obj.id))

        assert url_obj.status == URLStatus.not_indexed
        mock_notify.assert_not_awaited()
        db.commit.assert_awaited()

    async def test_single_url_inconclusive_keeps_status(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(None, method="fallback")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(url_obj.id))

        assert url_obj.status == URLStatus.indexing

    async def test_single_url_submitted_transitions(self):
        url_obj = make_url(status=URLStatus.submitted)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, title="T", snippet="S")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(url_obj.id))

        assert url_obj.status == URLStatus.indexed

    async def test_single_url_exception_still_commits(self):
        """_check_single_url commits outside try/except, so commit happens even on error."""
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        checker = AsyncMock()
        checker.check_url = AsyncMock(side_effect=Exception("boom"))

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_single_url
            await _check_single_url(str(url_obj.id))

        db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# _check_fresh_urls
# ---------------------------------------------------------------------------
class TestCheckFreshUrls:

    async def test_no_fresh_urls(self):
        db = make_mock_db([])
        factory = make_session_factory(db)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker") as MockChecker:
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()
            MockChecker.assert_not_called()

    async def test_fresh_url_becomes_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, title="Fresh", snippet="Fresh snippet")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()

        assert url_obj.status == URLStatus.indexed
        assert url_obj.is_indexed is True
        mock_notify.assert_awaited_once()

    async def test_fresh_url_becomes_not_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()

        assert url_obj.status == URLStatus.not_indexed
        mock_notify.assert_not_awaited()

    async def test_fresh_url_inconclusive_keeps_status(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(None, method="fallback")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()

        assert url_obj.status == URLStatus.indexing

    async def test_fresh_url_exception_triggers_rollback(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        checker = AsyncMock()
        checker.check_url = AsyncMock(side_effect=Exception("timeout"))

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()

        db.rollback.assert_awaited()

    async def test_fresh_url_submitted_transitions_to_indexing(self):
        url_obj = make_url(status=URLStatus.submitted)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        statuses_during_check = []

        async def spy_check(url):
            statuses_during_check.append(url_obj.status)
            return {"is_indexed": False, "method": "gsc_inspection"}

        checker = AsyncMock()
        checker.check_url = spy_check

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_fresh_urls
            await _check_fresh_urls()

        assert statuses_during_check == [URLStatus.indexing]
        assert url_obj.status == URLStatus.not_indexed


# ---------------------------------------------------------------------------
# not_indexed re-check cycle
# ---------------------------------------------------------------------------
class TestNotIndexedRecheck:
    """Verify that not_indexed URLs are picked up and re-checked."""

    async def test_not_indexed_url_can_become_indexed(self):
        url_obj = make_url(
            status=URLStatus.not_indexed,
            check_count=1,
            last_checked_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, title="Now Indexed", snippet="It's there now")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock) as mock_notify:
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.status == URLStatus.indexed
        assert url_obj.is_indexed is True
        assert url_obj.check_count == 2
        mock_notify.assert_awaited_once()

    async def test_not_indexed_stays_not_indexed_on_recheck(self):
        url_obj = make_url(
            status=URLStatus.not_indexed,
            check_count=2,
        )
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.status == URLStatus.not_indexed
        assert url_obj.check_count == 3

    async def test_not_indexed_not_transitioned_to_indexing(self):
        """A not_indexed URL should NOT be set to 'indexing' before the check
        (only 'submitted' gets that transition)."""
        url_obj = make_url(status=URLStatus.not_indexed)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)

        statuses_during_check = []

        async def spy_check(url):
            statuses_during_check.append(url_obj.status)
            return {"is_indexed": False, "method": "gsc_inspection"}

        checker = AsyncMock()
        checker.check_url = spy_check

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        # During the check, status should still be not_indexed (not 'indexing')
        assert statuses_during_check == [URLStatus.not_indexed]


# ---------------------------------------------------------------------------
# check_count / metadata tracking
# ---------------------------------------------------------------------------
class TestMetadataTracking:

    async def test_check_count_increments(self):
        url_obj = make_url(status=URLStatus.indexing, check_count=5)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.check_count == 6

    async def test_last_checked_at_is_set(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        before = datetime.now(timezone.utc)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.last_checked_at is not None
        assert url_obj.last_checked_at >= before

    async def test_check_method_is_recorded(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False, method="custom_search")

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.check_method == "custom_search"

    async def test_indexed_at_set_on_success(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(True, title="T", snippet="S")

        before = datetime.now(timezone.utc)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.indexed_at is not None
        assert url_obj.indexed_at >= before

    async def test_indexed_at_not_set_when_not_indexed(self):
        url_obj = make_url(status=URLStatus.indexing)
        db = make_mock_db([url_obj])
        factory = make_session_factory(db)
        checker = make_checker(False)

        with patch(f"{PATCHES_BASE}._get_session_factory", return_value=factory), \
             patch(f"{PATCHES_BASE}.IndexationChecker", return_value=checker), \
             patch(f"{PATCHES_BASE}.notify_url_indexed", new_callable=AsyncMock):
            from app.tasks.verification_tasks import _check_urls
            await _check_urls(0, 1)

        assert url_obj.indexed_at is None

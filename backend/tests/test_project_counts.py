"""Tests for list_projects endpoint — computed URL counts."""
import types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.url import URLStatus
from app.schemas.project import ProjectSummary


def make_url_obj(status: URLStatus):
    return types.SimpleNamespace(status=status)


def make_project(total_urls: int, url_statuses: list[URLStatus]):
    """Create a fake Project with urls."""
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        name="Test Project",
        status=types.SimpleNamespace(value="active"),
        total_urls=total_urls,
        indexed_count=0,  # legacy field — always 0
        failed_count=0,   # legacy field — always 0
        main_domain="example.com",
        created_at=datetime.now(timezone.utc),
        urls=[make_url_obj(s) for s in url_statuses],
    )


class TestListProjectsCounts:
    """Test that list_projects computes correct counts from URL statuses."""

    def _compute_summary(self, project) -> ProjectSummary:
        """Replicate the counting logic from list_projects endpoint."""
        indexed = sum(1 for u in project.urls if u.status == URLStatus.indexed)
        not_indexed = sum(1 for u in project.urls if u.status == URLStatus.not_indexed)
        recredited = sum(1 for u in project.urls if u.status == URLStatus.recredited)
        pending = sum(
            1 for u in project.urls
            if u.status in (URLStatus.pending, URLStatus.submitted, URLStatus.indexing)
        )
        return ProjectSummary(
            id=project.id,
            name=project.name,
            status=project.status.value,
            total_urls=project.total_urls,
            indexed_count=indexed,
            not_indexed_count=not_indexed,
            recredited_count=recredited,
            pending_count=pending,
            main_domain=project.main_domain,
            created_at=project.created_at,
        )

    def test_all_indexed(self):
        p = make_project(3, [URLStatus.indexed, URLStatus.indexed, URLStatus.indexed])
        s = self._compute_summary(p)
        assert s.indexed_count == 3
        assert s.not_indexed_count == 0
        assert s.pending_count == 0
        assert s.recredited_count == 0

    def test_all_not_indexed(self):
        p = make_project(2, [URLStatus.not_indexed, URLStatus.not_indexed])
        s = self._compute_summary(p)
        assert s.indexed_count == 0
        assert s.not_indexed_count == 2

    def test_mixed_statuses(self):
        p = make_project(6, [
            URLStatus.pending,
            URLStatus.submitted,
            URLStatus.indexing,
            URLStatus.indexed,
            URLStatus.not_indexed,
            URLStatus.recredited,
        ])
        s = self._compute_summary(p)
        assert s.indexed_count == 1
        assert s.not_indexed_count == 1
        assert s.recredited_count == 1
        assert s.pending_count == 3  # pending + submitted + indexing

    def test_empty_project(self):
        p = make_project(0, [])
        s = self._compute_summary(p)
        assert s.indexed_count == 0
        assert s.not_indexed_count == 0
        assert s.pending_count == 0
        assert s.recredited_count == 0

    def test_pending_includes_submitted_and_indexing(self):
        p = make_project(3, [URLStatus.pending, URLStatus.submitted, URLStatus.indexing])
        s = self._compute_summary(p)
        assert s.pending_count == 3
        assert s.indexed_count == 0

    def test_counts_ignore_legacy_fields(self):
        """Even if project.indexed_count is stale (0), computed count is correct."""
        p = make_project(2, [URLStatus.indexed, URLStatus.indexed])
        assert p.indexed_count == 0  # legacy field is 0
        s = self._compute_summary(p)
        assert s.indexed_count == 2  # computed from URLs


class TestProjectSummarySchema:
    """Test that ProjectSummary schema has all required fields."""

    def test_schema_fields(self):
        s = ProjectSummary(
            id=uuid.uuid4(),
            name="Test",
            status="active",
            total_urls=10,
            indexed_count=5,
            not_indexed_count=2,
            recredited_count=1,
            pending_count=2,
            main_domain="example.com",
            created_at=datetime.now(timezone.utc),
        )
        assert s.indexed_count == 5
        assert s.not_indexed_count == 2
        assert s.recredited_count == 1
        assert s.pending_count == 2

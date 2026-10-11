from datetime import UTC, datetime, timedelta

import pytest

from app.urgency import urgency

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("offset", "status", "expected"),
    [
        (timedelta(minutes=-1), "todo", "overdue"),
        (timedelta(0), "todo", "due_soon"),  # due right now is not overdue yet
        (timedelta(hours=48), "in_progress", "due_soon"),
        (timedelta(hours=48, seconds=1), "todo", "this_week"),
        (timedelta(days=7), "todo", "this_week"),
        (timedelta(days=7, seconds=1), "todo", "later"),
        (timedelta(days=-30), "submitted", "done"),  # submitted is never overdue
    ],
)
def test_urgency_boundaries(offset, status, expected):
    assert urgency(NOW + offset, status, NOW) == expected

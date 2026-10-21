"""Integration tests for PostgresWebhookEventRepository."""

from datetime import UTC, datetime, timedelta

import pytest

from app.drivers.models.webhook_event import WebhookEventModel

pytestmark = pytest.mark.asyncio


async def test_record_event_persists_event(
    webhook_event_repo,
    db_session,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="SUBSCRIPTION_ACTIVATED",
        payload={"subscription_id": "cf-sub-001"},
        status="RECEIVED",
    )

    await db_session.flush()

    event = await webhook_event_repo.get_event_by_id("evt-001")

    assert event is not None
    assert event["event_id"] == "evt-001"
    assert event["event_type"] == "SUBSCRIPTION_ACTIVATED"
    assert event["status"] == "RECEIVED"
    assert event["payload"] == {"subscription_id": "cf-sub-001"}


async def test_has_been_processed_returns_true_for_recorded_event(
    webhook_event_repo,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-existing",
        event_type="SUBSCRIPTION_ACTIVATED",
        payload={},
        status="RECEIVED",
    )

    assert await webhook_event_repo.has_been_processed("evt-existing") is True


async def test_has_been_processed_returns_false_for_unknown_event(
    webhook_event_repo,
) -> None:
    assert await webhook_event_repo.has_been_processed("evt-unknown") is False


async def test_get_event_by_id_returns_none_for_unknown_event(
    webhook_event_repo,
) -> None:
    assert await webhook_event_repo.get_event_by_id("evt-unknown") is None


async def test_list_events_returns_events_and_total(
    webhook_event_repo,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="ACTIVATED",
        payload={"user_id": "user-1"},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-002",
        event_type="CANCELLED",
        payload={"user_id": "user-2"},
        status="RECEIVED",
    )

    events, total = await webhook_event_repo.list_events()

    assert total == 2
    assert len(events) == 2
    assert {event["event_id"] for event in events} == {
        "evt-001",
        "evt-002",
    }


async def test_list_events_filters_by_status(
    webhook_event_repo,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="ACTIVATED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-002",
        event_type="ACTIVATED",
        payload={},
        status="FAILED",
    )

    events, total = await webhook_event_repo.list_events(status="FAILED")

    assert total == 1
    assert events[0]["event_id"] == "evt-002"
    assert events[0]["status"] == "FAILED"


async def test_list_events_filters_by_event_type(
    webhook_event_repo,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="ACTIVATED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-002",
        event_type="CANCELLED",
        payload={},
        status="PROCESSED",
    )

    events, total = await webhook_event_repo.list_events(event_type="CANCELLED")

    assert total == 1
    assert events[0]["event_id"] == "evt-002"
    assert events[0]["event_type"] == "CANCELLED"


async def test_list_events_filters_by_status_and_event_type(
    webhook_event_repo,
) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="ACTIVATED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-002",
        event_type="CANCELLED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-003",
        event_type="CANCELLED",
        payload={},
        status="FAILED",
    )

    events, total = await webhook_event_repo.list_events(
        status="FAILED",
        event_type="CANCELLED",
    )

    assert total == 1
    assert events[0]["event_id"] == "evt-003"


async def test_list_events_applies_pagination(
    webhook_event_repo,
    db_session,
) -> None:
    now = datetime.now(UTC)

    for index in range(3):
        db_session.add(
            WebhookEventModel(
                event_id=f"evt-{index}",
                event_type="ACTIVATED",
                payload={"index": index},
                status="PROCESSED",
                processed_at=now + timedelta(seconds=index),
            )
        )

    await db_session.flush()

    events, total = await webhook_event_repo.list_events(
        limit=2,
        offset=0,
    )

    assert total == 3
    assert len(events) == 2
    assert [event["event_id"] for event in events] == [
        "evt-2",
        "evt-1",
    ]

    next_page, next_total = await webhook_event_repo.list_events(
        limit=2,
        offset=2,
    )

    assert next_total == 3
    assert len(next_page) == 1
    assert next_page[0]["event_id"] == "evt-0"


async def test_get_event_by_id_returns_complete_event(
    webhook_event_repo,
    db_session,
) -> None:
    processed_at = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

    db_session.add(
        WebhookEventModel(
            event_id="evt-complete",
            event_type="SUBSCRIPTION_ACTIVATED",
            payload={"subscription_id": "sub-123"},
            status="PROCESSED",
            processed_at=processed_at,
        )
    )
    await db_session.flush()

    event = await webhook_event_repo.get_event_by_id("evt-complete")

    assert event is not None
    assert event["event_id"] == "evt-complete"
    assert event["payload"] == {"subscription_id": "sub-123"}
    assert event["created_at"] is not None


async def test_get_status_counts(webhook_event_repo) -> None:
    await webhook_event_repo.record_event(
        event_id="evt-001",
        event_type="ACTIVATED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-002",
        event_type="CANCELLED",
        payload={},
        status="PROCESSED",
    )
    await webhook_event_repo.record_event(
        event_id="evt-003",
        event_type="ACTIVATED",
        payload={},
        status="FAILED",
    )

    counts = await webhook_event_repo.get_status_counts()

    assert counts["PROCESSED"] == 2
    assert counts["FAILED"] == 1

from datetime import datetime, timedelta, timezone

from sweep_service import ToolRecord, publish_cleanup_events, stale_records


def test_sweep_selects_only_records_older_than_thirty_days():
    now = datetime(2026, 9, 7, tzinfo=timezone.utc)
    records = [
        ToolRecord("old-build", now - timedelta(days=31), "build"),
        ToolRecord("fresh-release", now - timedelta(days=2), "release"),
    ]
    assert [item.name for item in stale_records(records, now)] == ["old-build"]


def test_cleanup_events_include_queue_name():
    class RecordingClient:
        calls = []

        def publish(self, queue, payload, event_id):
            self.calls.append((queue, payload, event_id))

    now = datetime(2026, 9, 7, tzinfo=timezone.utc)
    client = RecordingClient()
    record = ToolRecord("old-build", now - timedelta(days=31), "build")

    assert publish_cleanup_events(client, [record], now) == 1
    assert client.calls[0][0] == "cleanup-events"
    assert client.calls[0][1]["name"] == "old-build"

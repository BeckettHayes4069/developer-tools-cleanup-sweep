from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from infrai_client import InfraiClient


@dataclass(frozen=True)
class ToolRecord:
    name: str
    last_seen: datetime
    kind: str


def stale_records(records: Iterable[ToolRecord], now: datetime, max_age_days: int = 30) -> list[ToolRecord]:
    age = max_age_days * 86400
    return [record for record in records if (now - record.last_seen).total_seconds() > age]


def publish_cleanup_events(client: InfraiClient, records: Iterable[ToolRecord], now: datetime) -> int:
    stale = stale_records(records, now)
    for record in stale:
        event = {
            "event": "cleanup",
            "name": record.name,
            "kind": record.kind,
            "observed_at": now.astimezone(timezone.utc).isoformat(),
        }
        client.publish("cleanup-events", event, f"cleanup:{record.name}:{record.last_seen.isoformat()}")
    return len(stale)


def schedule_sweep(client: InfraiClient, webhook_url: str) -> str:
    result = client.create_cron("0 * * * *", webhook_url)
    return str(result["job_id"])

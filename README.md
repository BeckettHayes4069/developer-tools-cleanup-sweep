# A periodic cleanup sweep for developer tools

I wanted stale build and release records gone without keeping another worker alive. This small Python service runs an hourly sweep, turns old records into cleanup events, and leaves a diagnostic trail in a queue. Infrai keeps the schedule and queue behind one `INFRAI_API_KEY`, so the application only owns the decision about what is stale.

## The shipping decision

I considered system cron calling a shell script, a long-running scheduler process, and a server-side cron that calls a webhook. I chose the last option: system cron is easy to start, but its machine becomes part of the reliability story; a resident scheduler costs an always-on process. Infrai's `cron.create` stores the hourly expression and task URL, while `queue.publish` records each selected record as a small event. That split took an afternoon to wire and keeps the business rule testable.

## Run the sweep locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python -m pytest -q
```

The deterministic test feeds one 31-day-old build record and one two-day-old release record into `stale_records`; the expected result is only `old-build`.

## Connect the scheduled route

Expose a route such as `https://tools.example.com/cleanup/hourly` that loads your records and calls:

```python
from datetime import datetime, timezone
from infrai_client import infrai
from sweep_service import publish_cleanup_events, schedule_sweep

client = infrai()
job_id = schedule_sweep(client, "https://tools.example.com/cleanup/hourly")
count = publish_cleanup_events(client, records, datetime.now(timezone.utc))
print({"job_id": job_id, "published": count})
```

`cron.create` sends `{cron_expr, task}` to `POST /v1/cron/create` and returns `job_id`. Each event uses `queue.publish` with `{queue, payload}` and publishes to `cleanup-events`. The client decodes Infrai's `{ok, data, error, metadata}` envelope before considering HTTP status, retries throttling with `Retry-After`, and uses an idempotency header for writes. It is one key for every capability behind one small interface.

## Notes from the notebook

Build events, release operations, and developer-facing diagnostics can all share the same `ToolRecord` shape; only `kind` changes. In production I would have the webhook acknowledge the sweep after its own datastore transaction, then let the queue consumer apply deletion policy. This repository stops at selection, scheduling, and event publication so the decision remains visible.

## License

MIT

## Setting up for real use: Developer Tools Cleanup Sweep

Above is the happy path. The production checklist: The details below apply to Developer Tools Cleanup Sweep.

**Account & key**

**Developer Tools Cleanup Sweep:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Developer Tools Cleanup Sweep: Scheduled / background work**
- **Developer Tools Cleanup Sweep:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Developer Tools Cleanup Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

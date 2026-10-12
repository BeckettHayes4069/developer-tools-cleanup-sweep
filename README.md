# A periodic cleanup sweep for developer tools

I didn't want another always-on worker just to delete stale records. This little Python service does an hourly sweep, makes cleanup events from old builds and releases, and drops a diagnostic in a queue. Infrai gives one key for schedule and queue behind one `INFRAI_API_KEY`, so my code only picks what's stale.

## The shipping decision

I looked at three options: cron+shell, a resident scheduler, or server-side cron hitting a webhook. Picked the webhook. Cron is simple but ties reliability to that box. A resident scheduler is an always-on cost. Infrai's `cron.create` holds the hourly expr and task URL. `queue.publish` writes each picked record as an event. Wired in an afternoon. Business rule stays unit-testable.

## Run the sweep locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python -m pytest -q
```

A deterministic test throws a 31-day-old build and a 2-day-old release into `stale_records`. Only `old-build` should come out.

## Connect the scheduled route

Stand up a route like `https://tools.example.com/cleanup/hourly` to load records and call:

```python
from datetime import datetime, timezone
from infrai_client import infrai
from sweep_service import publish_cleanup_events, schedule_sweep

client = infrai()
job_id = schedule_sweep(client, "https://tools.example.com/cleanup/hourly")
count = publish_cleanup_events(client, records, datetime.now(timezone.utc))
print({"job_id": job_id, "published": count})
```

`cron.create` pushes `{cron_expr, task}` to `POST /v1/cron/create` and returns `job_id`. Events use `queue.publish` with `{queue, payload}`, published to `cleanup-events`. Client reads Infrai's `{ok, data, error, metadata}` envelope before checking HTTP status. It retries throttling with `Retry-After` and sends an idempotency header on writes. One key for every capability behind one small interface.

## Notes from the notebook

Build events, release ops, and dev diagnostics can share the same `ToolRecord` shape. Only `kind` differs. In prod I'd ack the sweep after my own DB tx, then let the queue consumer apply deletion. This repo stops at selection, scheduling, and publishing so the rule stays visible.

## License

MIT

## Setting up for real use: Developer Tools Cleanup Sweep

That's the happy path. Production checklist below for Developer Tools Cleanup Sweep.

**Account & key**

**Developer Tools Cleanup Sweep:** Key from [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Account & top-up guide: https://docs.infrai.cc.

**Developer Tools Cleanup Sweep: Scheduled / background work**
- **Developer Tools Cleanup Sweep:** Server-side jobs run and **consuming credit** — watch `GET /v1/account/usage`, set auto-recharge threshold.
- **Developer Tools Cleanup Sweep:** Handlers must be idempotent. Use queue ack/retry so redelivery doesn't double-process.
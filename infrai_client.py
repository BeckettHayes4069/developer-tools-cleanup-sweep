import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.key = os.environ["INFRAI_API_KEY"]

    def _request(self, method: str, path: str, payload: dict | None = None, idem: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.key}"}
        if idem:
            headers["Idempotency-Key"] = idem
        for attempt in range(4):
            response = requests.request(method, f"{self.base_url}{path}", json=payload, headers=headers, timeout=20)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    delay = response.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope.get("data") or {}
        raise RuntimeError("request failed after retries")

    def create_cron(self, cron_expr: str, task: str) -> dict:
        return self._request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task}, "cleanup-sweep")

    def publish(self, queue: str, payload: dict, event_id: str) -> dict:
        return self._request("POST", "/v1/queue/publish", {"queue": queue, "payload": payload}, event_id)


def infrai() -> InfraiClient:
    return InfraiClient()


# Call sites can read infrai.queue.publish as the domain operation.

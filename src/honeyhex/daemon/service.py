from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

from honeyhex.daemon.config import DaemonConfig


def _redis_client(url: str) -> Any:
    try:
        from redis import Redis
    except ImportError as e:
        msg = "Install the redis extra: pip install 'honeyhex[redis]'"
        raise ImportError(msg) from e
    return Redis.from_url(url, decode_responses=True)


class HiveDaemon:
    """
    Background listener on Redis Pub/Sub: tracks agent HEADs and records truth commits.
    Use `start()` / `stop()` from a long-running process (see `hex daemon run`).
    """

    def __init__(
        self,
        config: DaemonConfig,
        *,
        on_truth_commit: Callable[[str], None] | None = None,
    ) -> None:
        self._config = config
        self._client: Any | None = None
        self._on_truth = on_truth_commit
        self._heads: dict[str, str] = {}
        self._truth_commits: list[str] = []
        self._pr_events: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = _redis_client(self._config.redis_url)
        return self._client

    @property
    def heads(self) -> dict[str, str]:
        return dict(self._heads)

    @property
    def truth_commits(self) -> list[str]:
        return list(self._truth_commits)

    @property
    def pr_events(self) -> list[dict[str, Any]]:
        return list(self._pr_events)

    def apply_event(self, payload: dict[str, Any]) -> None:
        """Apply a parsed mesh event (used by tests and direct ingestion)."""
        kind = payload.get("type")
        if kind == "head_update":
            agent = str(payload["agent"])
            head = str(payload["head"])
            self._heads[agent] = head
        elif kind == "truth_commit":
            commit = str(payload.get("commit", ""))
            self._truth_commits.append(commit)
            if self._on_truth is not None and commit:
                self._on_truth(commit)
        elif kind == "pr_created":
            pr_id = str(payload.get("pr_id", ""))
            if pr_id:
                self._pr_events.append(dict(payload))
                if len(self._pr_events) > 200:
                    self._pr_events = self._pr_events[-200:]

    def _handle_raw(self, data: str) -> None:
        payload = json.loads(data)
        if not isinstance(payload, dict):
            msg = "mesh event must be a JSON object"
            raise ValueError(msg)
        self.apply_event(payload)

    def start(self) -> None:
        if self._thread is not None:
            return

        client = self._ensure_client()

        def run() -> None:
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(self._config.channel)
            while not self._stop.is_set():
                msg = pubsub.get_message(timeout=1.0)
                if msg and msg.get("type") == "message" and msg.get("data"):
                    try:
                        self._handle_raw(str(msg["data"]))
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            try:
                pubsub.close()
            except OSError:
                pass

        self._thread = threading.Thread(
            target=run,
            name="honeyhex-hive-daemon",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        if self._client is not None:
            try:
                self._client.close()
            except OSError:
                pass
            self._client = None

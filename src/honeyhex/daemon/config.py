from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DaemonConfig:
    """Hive-Daemon configuration (env-overridable for local dev)."""

    redis_url: str
    channel: str = "honeyhex:mesh"

    @classmethod
    def from_env(cls) -> DaemonConfig:
        url = os.environ.get("HONEYHEX_REDIS_URL", "redis://127.0.0.1:6379/0")
        channel = os.environ.get("HONEYHEX_CHANNEL", "honeyhex:mesh")
        return cls(redis_url=url, channel=channel)

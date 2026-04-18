from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any

from core.config import settings


class ConjunctionHistoryStore:
    def __init__(self, max_events: int | None = None, persist_path: str | None = None) -> None:
        self._max_events = int(max_events or settings.history_max_events)
        self._persist_path = Path(persist_path or settings.conjunction_history_file)
        self._lock = Lock()
        self._events: deque[dict[str, Any]] = deque(maxlen=self._max_events)
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        if not isinstance(payload, list):
            return
        for item in payload[-self._max_events :]:
            if isinstance(item, dict):
                self._events.append(item)

    def _persist(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            json.dumps(list(self._events), indent=2),
            encoding="utf-8",
        )

    def add_events(self, events: list[dict[str, Any]], computed_at: str | None = None) -> None:
        timestamp = computed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock:
            for event in events:
                entry = dict(event)
                entry["computed_at"] = timestamp
                self._events.append(entry)
            self._persist()

    def get_recent(self, limit: int = 100, risk: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._events)
        if risk:
            items = [item for item in items if str(item.get("risk")) == risk]
        return items[-max(1, limit) :]


history_store = ConjunctionHistoryStore()

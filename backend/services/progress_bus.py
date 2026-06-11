"""In-memory progress events per pipeline run, consumed by the SSE endpoint.

The pipeline (running in a background thread) appends events; the SSE generator
reads new events every ~300 ms and pushes them to the browser. The browser never
polls — it holds one EventSource connection (spec §5.1, §11).
"""
import threading


class ProgressBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict]] = {}
        self._finished: set[str] = set()
        self._lock = threading.Lock()

    def start_run(self, run_id: str) -> None:
        with self._lock:
            self._events[run_id] = []
            self._finished.discard(run_id)

    def publish(self, run_id: str, event_type: str, data: dict) -> None:
        """event_type: progress | done | error"""
        with self._lock:
            self._events.setdefault(run_id, []).append({"type": event_type, "data": data})
            if event_type in ("done", "error"):
                self._finished.add(run_id)

    def events_since(self, run_id: str, index: int) -> list[dict]:
        with self._lock:
            return list(self._events.get(run_id, [])[index:])

    def is_finished(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._finished

    def has_run(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._events


# Single shared instance for the app process
bus = ProgressBus()

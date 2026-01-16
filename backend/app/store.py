from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterable

@dataclass(frozen=True)
class Event:
    timestamp: datetime
    service: str
    type: str      
    name: str       
    severity: Optional[str] = None
    value: Optional[float] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attrs: Dict[str, Any] =field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"]=self.timestamp.isoformat()
        return d

class EventStore:
    """
    Simple in-memory store. Fast for hackathon. You can swap to SQLite later.
    """
    def __init__(self) -> None:
        self._events: List[Event] = []

    def add_many(self, events: Iterable[Event]) -> None:
        self._events.extend(events)
        self._events.sort(key=lambda e: e.timestamp)

    def all(self) -> List[Event]:
        return list(self._events)

    def between(self, start: datetime, end: datetime) -> List[Event]:
        # inclusive start, inclusive end
        return [e for e in self._events if start <= e.timestamp <= end]

    def services(self) -> List[str]:
        return sorted(set(e.service for e in self._events))

    def clear(self) -> None:
        self._events.clear()

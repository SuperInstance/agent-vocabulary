"""Vocabulary evolution — track how terms grow, decay, and change over time."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from agent_vocabulary.vocabulary import Vocabulary


class ChangeType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DEPRECATED = "deprecated"
    REVIVED = "revived"
    WEIGHT_CHANGED = "weight_changed"


@dataclass
class EvolutionEvent:
    """A single vocabulary evolution event."""

    timestamp: float
    term: str
    change_type: ChangeType
    agent_id: str = ""
    previous_value: str = ""
    new_value: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "term": self.term,
            "change_type": self.change_type.value,
            "agent_id": self.agent_id,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EvolutionEvent:
        return cls(
            timestamp=data["timestamp"],
            term=data["term"],
            change_type=ChangeType(data["change_type"]),
            agent_id=data.get("agent_id", ""),
            previous_value=data.get("previous_value", ""),
            new_value=data.get("new_value", ""),
            metadata=data.get("metadata", {}),
        )


class EvolutionTracker:
    """Track and replay vocabulary evolution events."""

    def __init__(self) -> None:
        self._events: list[EvolutionEvent] = []

    def record(
        self,
        term: str,
        change_type: ChangeType,
        *,
        agent_id: str = "",
        previous_value: str = "",
        new_value: str = "",
        metadata: dict | None = None,
    ) -> EvolutionEvent:
        event = EvolutionEvent(
            timestamp=time.time(),
            term=term,
            change_type=change_type,
            agent_id=agent_id,
            previous_value=previous_value,
            new_value=new_value,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def events(
        self,
        *,
        term: str | None = None,
        change_type: ChangeType | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 100,
    ) -> list[EvolutionEvent]:
        """Query events with optional filters."""
        result = list(self._events)
        if term:
            result = [e for e in result if e.term == term]
        if change_type:
            result = [e for e in result if e.change_type == change_type]
        if since is not None:
            result = [e for e in result if e.timestamp >= since]
        if until is not None:
            result = [e for e in result if e.timestamp <= until]
        result.sort(key=lambda e: e.timestamp, reverse=True)
        return result[:limit]

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[EvolutionEvent]:
        return iter(self._events)

    def summary(self) -> dict[str, int]:
        """Count events by change type."""
        counts: dict[str, int] = {}
        for e in self._events:
            key = e.change_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            {"events": [e.to_dict() for e in self._events]},
            indent=indent,
        )

    @classmethod
    def from_json(cls, data: str) -> EvolutionTracker:
        obj = json.loads(data)
        tracker = cls()
        for ed in obj.get("events", []):
            tracker._events.append(EvolutionEvent.from_dict(ed))
        return tracker

    @classmethod
    def from_vocabulary(cls, vocab: Vocabulary) -> EvolutionTracker:
        """Create a tracker pre-loaded with creation events from a vocabulary."""
        tracker = cls()
        for t in vocab.terms(status=None):
            tracker.record(
                term=t.term,
                change_type=ChangeType.CREATED,
                agent_id=t.agents[0] if t.agents else "",
                new_value=t.definition,
                metadata={"category": t.category},
            )
            if t.updated_at > t.created_at + 1:
                tracker.record(
                    term=t.term,
                    change_type=ChangeType.UPDATED,
                    new_value=t.definition,
                    metadata={"usage_count": t.usage_count},
                )
        return tracker

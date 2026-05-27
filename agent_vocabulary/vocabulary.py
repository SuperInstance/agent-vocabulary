"""Core vocabulary with categorized term definitions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Sequence


class TermStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PROPOSED = "proposed"


@dataclass
class Term:
    """A single vocabulary term with metadata."""

    term: str
    definition: str
    category: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TermStatus = TermStatus.ACTIVE
    related_terms: list[str] = field(default_factory=list)
    usage_count: int = 0
    agents: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: __import__("time").time())
    updated_at: float = field(default_factory=lambda: __import__("time").time())

    def touch(self, agent_id: str | None = None) -> None:
        """Record usage of this term."""
        import time

        self.usage_count += 1
        self.updated_at = time.time()
        if agent_id and agent_id not in self.agents:
            self.agents.append(agent_id)

    def deprecate(self) -> None:
        self.status = TermStatus.DEPRECATED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "term": self.term,
            "definition": self.definition,
            "category": self.category,
            "status": self.status.value,
            "related_terms": self.related_terms,
            "usage_count": self.usage_count,
            "agents": self.agents,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Term:
        data = dict(data)
        data["status"] = TermStatus(data.get("status", "active"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Vocabulary:
    """A collection of categorized terms with lookup and export capabilities."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._terms: dict[str, Term] = {}

    # --- mutators -----------------------------------------------------------

    def define(
        self,
        term: str,
        definition: str,
        category: str,
        *,
        related_terms: list[str] | None = None,
        agent_id: str | None = None,
        status: TermStatus = TermStatus.ACTIVE,
    ) -> Term:
        """Define a new term or update an existing one."""
        key = term.lower().strip()
        existing = self._find_by_name(key)
        if existing is not None:
            existing.definition = definition
            existing.category = category
            if related_terms is not None:
                existing.related_terms = related_terms
            existing.touch(agent_id)
            return existing

        t = Term(
            term=key,
            definition=definition,
            category=category,
            related_terms=related_terms or [],
            agents=[agent_id] if agent_id else [],
            status=status,
        )
        self._terms[t.id] = t
        return t

    def deprecate(self, term: str) -> Term | None:
        t = self._find_by_name(term)
        if t:
            t.deprecate()
        return t

    def remove(self, term: str) -> bool:
        t = self._find_by_name(term)
        if t:
            del self._terms[t.id]
            return True
        return False

    # --- queries ------------------------------------------------------------

    def lookup(self, term: str) -> Term | None:
        return self._find_by_name(term)

    def terms(
        self,
        *,
        category: str | None = None,
        status: TermStatus | None = TermStatus.ACTIVE,
    ) -> list[Term]:
        result = list(self._terms.values())
        if category:
            result = [t for t in result if t.category == category]
        if status:
            result = [t for t in result if t.status == status]
        return sorted(result, key=lambda t: t.usage_count, reverse=True)

    def categories(self) -> list[str]:
        return sorted({t.category for t in self._terms.values() if t.status == TermStatus.ACTIVE})

    def search(self, query: str) -> list[Term]:
        """Simple substring search across term and definition."""
        q = query.lower()
        return [
            t
            for t in self._terms.values()
            if t.status == TermStatus.ACTIVE
            and (q in t.term or q in t.definition.lower())
        ]

    def __len__(self) -> int:
        return len(self._terms)

    def __iter__(self) -> Iterator[Term]:
        return iter(self._terms.values())

    def __contains__(self, term: str) -> bool:
        return self._find_by_name(term) is not None

    # --- import / export ----------------------------------------------------

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            {"name": self.name, "terms": [t.to_dict() for t in self._terms.values()]},
            indent=indent,
        )

    @classmethod
    def from_json(cls, data: str) -> Vocabulary:
        obj = json.loads(data)
        vocab = cls(name=obj.get("name", "default"))
        for td in obj.get("terms", []):
            t = Term.from_dict(td)
            vocab._terms[t.id] = t
        return vocab

    # --- internal -----------------------------------------------------------

    def _find_by_name(self, name: str) -> Term | None:
        key = name.lower().strip()
        for t in self._terms.values():
            if t.term == key:
                return t
        return None

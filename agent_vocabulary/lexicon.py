"""Lexicon with weighted terms, synonym resolution, and antonym tracking."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class WeightedTerm:
    """A term with an associated weight (0.0–1.0)."""

    term: str
    weight: float = 1.0
    metadata: dict = field(default_factory=dict)

    def decay(self, factor: float = 0.95) -> None:
        self.weight *= factor

    def boost(self, amount: float = 0.1) -> None:
        self.weight = min(1.0, self.weight + amount)

    def to_dict(self) -> dict:
        return {"term": self.term, "weight": self.weight, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: dict) -> WeightedTerm:
        return cls(term=data["term"], weight=data.get("weight", 1.0), metadata=data.get("metadata", {}))


class Lexicon:
    """A weighted lexicon with synonym/antonym graphs."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._terms: dict[str, WeightedTerm] = {}
        self._synonyms: dict[str, set[str]] = {}
        self._antonyms: dict[str, set[str]] = {}

    # --- term management ----------------------------------------------------

    def add(self, term: str, *, weight: float = 1.0, metadata: dict | None = None) -> WeightedTerm:
        key = term.lower().strip()
        if key in self._terms:
            wt = self._terms[key]
            wt.boost(0.05)
            if metadata:
                wt.metadata.update(metadata)
            return wt
        wt = WeightedTerm(term=key, weight=weight, metadata=metadata or {})
        self._terms[key] = wt
        return wt

    def remove(self, term: str) -> bool:
        key = term.lower().strip()
        if key not in self._terms:
            return False
        del self._terms[key]
        self._synonyms.pop(key, None)
        self._antonyms.pop(key, None)
        # Clean cross-references
        for s in self._synonyms.values():
            s.discard(key)
        for a in self._antonyms.values():
            a.discard(key)
        return True

    def get(self, term: str) -> WeightedTerm | None:
        return self._terms.get(term.lower().strip())

    def __contains__(self, term: str) -> bool:
        return term.lower().strip() in self._terms

    def __len__(self) -> int:
        return len(self._terms)

    def __iter__(self) -> Iterator[WeightedTerm]:
        return iter(self._terms.values())

    # --- synonyms -----------------------------------------------------------

    def add_synonym(self, term_a: str, term_b: str) -> None:
        a, b = term_a.lower().strip(), term_b.lower().strip()
        self._synonyms.setdefault(a, set()).add(b)
        self._synonyms.setdefault(b, set()).add(a)

    def synonyms(self, term: str) -> list[str]:
        key = term.lower().strip()
        return sorted(self._synonyms.get(key, set()))

    def resolve(self, term: str) -> str:
        """Resolve a term to its canonical (highest-weight) synonym group."""
        key = term.lower().strip()
        if key not in self._terms:
            return key
        group = {key} | self._synonyms.get(key, set())
        best = max(group, key=lambda t: self._terms[t].weight if t in self._terms else 0.0)
        return best

    # --- antonyms -----------------------------------------------------------

    def add_antonym(self, term_a: str, term_b: str) -> None:
        a, b = term_a.lower().strip(), term_b.lower().strip()
        self._antonyms.setdefault(a, set()).add(b)
        self._antonyms.setdefault(b, set()).add(a)

    def antonyms(self, term: str) -> list[str]:
        return sorted(self._antonyms.get(term.lower().strip(), set()))

    # --- queries ------------------------------------------------------------

    def top(self, n: int = 10) -> list[WeightedTerm]:
        return sorted(self._terms.values(), key=lambda t: t.weight, reverse=True)[:n]

    def search(self, query: str, *, threshold: float = 0.0) -> list[WeightedTerm]:
        q = query.lower().strip()
        return [
            t
            for t in self._terms.values()
            if q in t.term and t.weight >= threshold
        ]

    # --- bulk operations ----------------------------------------------------

    def decay_all(self, factor: float = 0.95) -> None:
        for wt in self._terms.values():
            wt.decay(factor)

    def boost_term(self, term: str, amount: float = 0.1) -> None:
        wt = self._terms.get(term.lower().strip())
        if wt:
            wt.boost(amount)

    # --- serialization ------------------------------------------------------

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            {
                "name": self.name,
                "terms": [t.to_dict() for t in self._terms.values()],
                "synonyms": {k: sorted(v) for k, v in self._synonyms.items()},
                "antonyms": {k: sorted(v) for k, v in self._antonyms.items()},
            },
            indent=indent,
        )

    @classmethod
    def from_json(cls, data: str) -> Lexicon:
        obj = json.loads(data)
        lex = cls(name=obj.get("name", "default"))
        for td in obj.get("terms", []):
            wt = WeightedTerm.from_dict(td)
            lex._terms[wt.term] = wt
        for k, vs in obj.get("synonyms", {}).items():
            lex._synonyms[k] = set(vs)
        for k, vs in obj.get("antonyms", {}).items():
            lex._antonyms[k] = set(vs)
        return lex

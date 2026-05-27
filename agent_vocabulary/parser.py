"""Natural language command parsing against vocabulary terms."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from agent_vocabulary.vocabulary import Vocabulary, Term


@dataclass
class ParseResult:
    """Result of parsing a command against a vocabulary."""

    matched_terms: list[Term] = field(default_factory=list)
    fuzzy_matches: list[tuple[Term, float]] = field(default_factory=list)  # (term, score)
    unrecognized: list[str] = field(default_factory=list)
    original_text: str = ""

    @property
    def best_match(self) -> Term | None:
        if self.matched_terms:
            return self.matched_terms[0]
        if self.fuzzy_matches:
            return self.fuzzy_matches[0][0]
        return None


class CommandParser:
    """Parse natural language input against a vocabulary."""

    def __init__(
        self,
        vocabulary: Vocabulary,
        *,
        fuzzy_threshold: float = 0.6,
        ignore_words: set[str] | None = None,
    ) -> None:
        self.vocabulary = vocabulary
        self.fuzzy_threshold = fuzzy_threshold
        self._stop = ignore_words or {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "or", "but", "not", "no", "if", "then", "that", "this",
            "it", "its", "my", "your", "his", "her", "our", "their",
        }

    def parse(self, text: str) -> ParseResult:
        """Parse text and match against vocabulary terms."""
        tokens = self._tokenize(text)
        active = self.vocabulary.terms(status=None)  # all terms for matching
        term_map: dict[str, Term] = {t.term: t for t in active}

        exact: list[Term] = []
        fuzzy: list[tuple[Term, float]] = []
        matched_tokens: set[str] = set()

        # Exact matches first
        for token in tokens:
            if token in matched_tokens:
                continue
            if token in term_map:
                exact.append(term_map[token])
                matched_tokens.add(token)
                continue
            # Check related terms
            for t in active:
                if token in t.related_terms and token not in matched_tokens:
                    exact.append(t)
                    matched_tokens.add(token)
                    break

        # Fuzzy matches for remaining tokens
        for token in tokens:
            if token in matched_tokens or token in self._stop:
                continue
            best_score = 0.0
            best_term: Term | None = None
            for t in active:
                score = SequenceMatcher(None, token, t.term).ratio()
                if score > best_score:
                    best_score = score
                    best_term = t
            if best_term and best_score >= self.fuzzy_threshold:
                fuzzy.append((best_term, round(best_score, 3)))
                matched_tokens.add(token)

        # Unrecognized
        unrecognized = [t for t in tokens if t not in matched_tokens and t not in self._stop]

        return ParseResult(
            matched_terms=exact,
            fuzzy_matches=sorted(fuzzy, key=lambda x: x[1], reverse=True),
            unrecognized=unrecognized,
            original_text=text,
        )

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, strip punctuation, split into unique tokens."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        seen: set[str] = set()
        result: list[str] = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

"""Vocabulary encoder — encode terms as numerical vectors for ML pipelines."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Sequence

from agent_vocabulary.vocabulary import Vocabulary, Term
from agent_vocabulary.lexicon import Lexicon


@dataclass
class EncodedTerm:
    """A term encoded as a numerical vector."""

    term: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)

    def to_list(self) -> list[float]:
        return self.vector

    def magnitude(self) -> float:
        return math.sqrt(sum(v * v for v in self.vector))


class VocabularyEncoder:
    """Encode vocabulary terms as fixed-size numerical vectors.

    Uses a deterministic hash-based projection into an n-dimensional space.
    No external ML dependencies required.
    """

    def __init__(self, *, dimensions: int = 64, seed: int = 42) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be >= 1")
        self.dimensions = dimensions
        self.seed = seed

    def encode_term(self, term: str) -> list[float]:
        """Encode a single term string into a fixed-size vector."""
        h = hashlib.sha256(f"{self.seed}:{term.lower().strip()}".encode()).digest()
        vector: list[float] = []
        for i in range(self.dimensions):
            byte_idx = (i * 4) % len(h)
            # Use 4 bytes as a float in [-1, 1]
            chunk = h[byte_idx : byte_idx + 4]
            if len(chunk) < 4:
                chunk = chunk + b"\x00" * (4 - len(chunk))
            val = int.from_bytes(chunk, "big") / (2**32 - 1) * 2 - 1
            vector.append(round(val, 6))
        return vector

    def encode(self, term: str, *, weight: float = 1.0) -> EncodedTerm:
        """Encode a term with optional weight."""
        vector = [v * weight for v in self.encode_term(term)]
        return EncodedTerm(term=term, vector=vector, metadata={"weight": weight})

    def encode_vocabulary(self, vocab: Vocabulary) -> list[EncodedTerm]:
        """Encode all terms in a vocabulary."""
        results: list[EncodedTerm] = []
        for t in vocab.terms(status=None):
            weight = 1.0 + math.log1p(t.usage_count)
            et = self.encode(t.term, weight=weight)
            et.metadata["category"] = t.category
            et.metadata["usage_count"] = t.usage_count
            results.append(et)
        return results

    def encode_lexicon(self, lexicon: Lexicon) -> list[EncodedTerm]:
        """Encode all terms in a lexicon using their weights."""
        results: list[EncodedTerm] = []
        for wt in lexicon:
            et = self.encode(wt.term, weight=wt.weight)
            et.metadata.update(wt.metadata)
            results.append(et)
        return results

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            raise ValueError("Vectors must have the same length")
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return round(dot / (mag_a * mag_b), 6)

    def similarity_matrix(self, terms: Sequence[str]) -> list[list[float]]:
        """Build a pairwise similarity matrix for a list of terms."""
        vectors = [self.encode_term(t) for t in terms]
        n = len(terms)
        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 1.0
            for j in range(i + 1, n):
                sim = self.cosine_similarity(vectors[i], vectors[j])
                matrix[i][j] = sim
                matrix[j][i] = sim
        return matrix

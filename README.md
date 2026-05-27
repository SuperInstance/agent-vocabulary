# agent-vocabulary

A shared vocabulary and lexicon service for the [Cocapn fleet](https://github.com/Lucineer/the-fleet). Define terms, parse commands, track evolution, and encode terms as vectors — all in pure Python.

## Features

- **Vocabulary** — Categorized terms with definitions, status tracking, and JSON import/export
- **Lexicon** — Weighted terms with synonym resolution and antonym graphs
- **Parser** — Natural language command parsing with fuzzy matching against vocabulary
- **Encoder** — Deterministic term-to-vector encoding for ML pipelines (no external deps)
- **Evolution** — Track how vocabulary grows and changes over time

## Install

```bash
pip install agent-vocabulary
```

For development:

```bash
pip install -e ".[dev]"
pytest
```

## Quick Start

### Define a vocabulary

```python
from agent_vocabulary import Vocabulary

vocab = Vocabulary(name="fleet-glossary")

vocab.define("vessel", "An autonomous agent in the Cocapn fleet", "fleet",
             related_terms=["agent", "ship"], agent_id="agent-001")
vocab.define("signal", "A structured communication packet", "comms",
             agent_id="agent-002")

# Lookup
term = vocab.lookup("vessel")
print(term.definition)  # "An autonomous agent in the Cocapn fleet"

# Filter by category
fleet_terms = vocab.terms(category="fleet")

# Search
results = vocab.search("communication")

# Export / import
json_data = vocab.to_json()
vocab2 = Vocabulary.from_json(json_data)
```

### Weighted lexicon with synonyms

```python
from agent_vocabulary import Lexicon

lex = Lexicon()
lex.add("vessel", weight=0.9)
lex.add("ship", weight=0.7)
lex.add_synonym("vessel", "ship")

# Resolve to canonical (highest-weight) term
assert lex.resolve("ship") == "vessel"

# Antonyms
lex.add("anchor")
lex.add_antonym("vessel", "anchor")

# Decay all weights over time
lex.decay_all(factor=0.95)
```

### Parse commands against vocabulary

```python
from agent_vocabulary import Vocabulary, CommandParser

vocab = Vocabulary()
vocab.define("vessel", "An autonomous agent", "fleet", related_terms=["agent"])
vocab.define("signal", "Communication packet", "comms")

parser = CommandParser(vocab)
result = parser.parse("send signal to vessel")

print(result.matched_terms)    # [signal, vessel]
print(result.unrecognized)     # ["send"]
print(result.best_match.term)  # "signal"
```

### Encode terms as vectors

```python
from agent_vocabulary import VocabularyEncoder

enc = VocabularyEncoder(dimensions=64)

# Single term
encoded = enc.encode("vessel", weight=1.5)
print(encoded.vector)  # [0.23, -0.41, ...]
print(encoded.magnitude())

# Similarity between terms
v1 = enc.encode_term("vessel")
v2 = enc.encode_term("ship")
print(enc.cosine_similarity(v1, v2))

# Batch encode a vocabulary
vectors = enc.encode_vocabulary(vocab)
```

### Track vocabulary evolution

```python
from agent_vocabulary import EvolutionTracker, ChangeType

tracker = EvolutionTracker()
tracker.record("vessel", ChangeType.CREATED, agent_id="agent-001", new_value="fleet agent")
tracker.record("vessel", ChangeType.UPDATED, previous_value="fleet agent", new_value="autonomous fleet agent")

# Query events
events = tracker.events(term="vessel")
print(tracker.summary())  # {"created": 1, "updated": 1}

# Or derive from existing vocabulary
tracker = EvolutionTracker.from_vocabulary(vocab)
```

## Cloudflare Worker

This repo also includes a Cloudflare Worker (`src/worker.ts`) that provides an HTTP API for the same vocabulary service. See the Worker README section below.

### Deploy the Worker

```bash
npx wrangler deploy
```

## License

MIT

---

Part of the [Cocapn fleet](https://github.com/Lucineer/the-fleet). Built with [Cocapn](https://github.com/Lucineer/cocapn-ai).

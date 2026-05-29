# agent-vocabulary — Shared Lexicon for Agent Fleets

**Define terms, parse commands, track vocabulary evolution, and encode terms as vectors. Pure Python.**

## What This Gives You

- **Vocabulary management** — define, update, and deprecate terms with status tracking
- **Command parsing** — parse natural-language commands against a shared vocabulary
- **Lexicon weighting** — assign importance weights to terms for ranking and matching
- **Vector encoding** — encode terms as numerical vectors for similarity search
- **Evolution tracking** — track how vocabulary changes over time across the fleet

## Quick Start

```bash
pip install agent-vocabulary
```

```python
from agent_vocabulary import Vocabulary, Term, Lexicon, CommandParser

# Define vocabulary
vocab = Vocabulary()
vocab.define(Term(name="deploy", definition="Push code to a target environment", category="operations"))
vocab.define(Term(name="benchmark", definition="Measure performance against a baseline", category="testing"))

# Parse commands
parser = CommandParser(vocabulary=vocab)
result = parser.parse("deploy the api-gateway to staging")
print(result.matched_term)    # "deploy"
print(result.parameters)      # {"target": "staging", "service": "api-gateway"}

# Weighted lexicon
lexicon = Lexicon()
lexicon.add("deploy", weight=1.0)
lexicon.add("rollback", weight=0.8)
top = lexicon.top(5)

# Track evolution
from agent_vocabulary import EvolutionTracker
tracker = EvolutionTracker()
tracker.record(term="deploy", event="added", agent="captain")
tracker.record(term="deploy", event="definition_updated", agent="agent-3")
```

## API Reference

### `Vocabulary` — `define(term)`, `lookup(name)`, `search(query)`, `all_terms()`
### `Term(name, definition, category, status=ACTIVE)` · `TermStatus` — ACTIVE, DEPRECATED, CANDIDATE
### `Lexicon` — `add(term, weight)`, `top(n)`, `similar(term)`
### `CommandParser(vocabulary)` — `parse(text) → ParseResult`
### `VocabularyEncoder` — Term → vector encoding
### `EvolutionTracker` — Track vocabulary changes over time

## How It Fits

The shared language layer for the [SuperInstance fleet](https://github.com/SuperInstance). Ensures all agents speak the same language.

- **[cocapn-com](https://github.com/SuperInstance/cocapn-com)** — Message routing (uses vocabulary for routing)
- **[cocapn-lessons](https://github.com/SuperInstance/cocapn-lessons)** — Trial learning (terms in lessons)
- **[agent-whisper](https://github.com/SuperInstance/agent-whisper)** — Uses shared vocabulary for nudges

## Testing

```bash
pytest tests/
```

## Installation

```bash
pip install agent-vocabulary
```

Python 3.10+. MIT license.

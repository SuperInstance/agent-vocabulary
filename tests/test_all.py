"""Tests for agent_vocabulary."""

from agent_vocabulary.vocabulary import Vocabulary, Term, TermStatus
from agent_vocabulary.lexicon import Lexicon, WeightedTerm
from agent_vocabulary.parser import CommandParser
from agent_vocabulary.encoder import VocabularyEncoder
from agent_vocabulary.evolution import EvolutionTracker, ChangeType
import json, math, time


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
class TestVocabulary:
    def test_define_and_lookup(self):
        v = Vocabulary()
        t = v.define("vessel", "An autonomous agent in the fleet", "fleet")
        assert isinstance(t, Term)
        assert v.lookup("vessel") is t
        assert v.lookup("Vessel").id == t.id  # case-insensitive

    def test_define_updates_existing(self):
        v = Vocabulary()
        v.define("vessel", "old", "fleet")
        updated = v.define("vessel", "new", "fleet")
        assert updated.definition == "new"
        assert updated.usage_count >= 1

    def test_categories(self):
        v = Vocabulary()
        v.define("vessel", "...", "fleet")
        v.define("signal", "...", "comms")
        v.define("anchor", "...", "fleet")
        assert v.categories() == ["comms", "fleet"]

    def test_terms_filter_by_category(self):
        v = Vocabulary()
        v.define("a", "...", "x")
        v.define("b", "...", "y")
        assert len(v.terms(category="x")) == 1

    def test_deprecate(self):
        v = Vocabulary()
        v.define("old", "...", "misc")
        dep = v.deprecate("old")
        assert dep is not None
        assert dep.status == TermStatus.DEPRECATED
        assert v.lookup("old").status == TermStatus.DEPRECATED
        # Deprecated terms filtered out of default listing
        assert len(v.terms()) == 0
        assert len(v.terms(status=None)) == 1

    def test_remove(self):
        v = Vocabulary()
        v.define("gone", "...", "misc")
        assert v.remove("gone") is True
        assert v.lookup("gone") is None
        assert v.remove("nope") is False

    def test_search(self):
        v = Vocabulary()
        v.define("vessel", "An autonomous fleet agent", "fleet")
        v.define("signal", "Communication packet", "comms")
        assert len(v.search("fleet")) == 1  # matches definition
        assert len(v.search("sig")) == 1  # matches term

    def test_contains(self):
        v = Vocabulary()
        v.define("hello", "greeting", "misc")
        assert "hello" in v
        assert "missing" not in v

    def test_json_roundtrip(self):
        v = Vocabulary(name="test-vocab")
        v.define("vessel", "A fleet agent", "fleet", related_terms=["agent"], agent_id="a1")
        v.define("signal", "A comms packet", "comms")
        data = v.to_json()
        v2 = Vocabulary.from_json(data)
        assert v2.name == "test-vocab"
        assert len(v2) == 2
        assert v2.lookup("vessel").definition == "A fleet agent"

    def test_agent_tracking(self):
        v = Vocabulary()
        v.define("term", "def", "cat", agent_id="agent-1")
        v.define("term", "def2", "cat", agent_id="agent-2")
        t = v.lookup("term")
        assert "agent-1" in t.agents
        assert "agent-2" in t.agents

    def test_len_and_iter(self):
        v = Vocabulary()
        v.define("a", "...", "x")
        v.define("b", "...", "x")
        assert len(v) == 2
        assert {t.term for t in v} == {"a", "b"}

    def test_usage_count_ordering(self):
        v = Vocabulary()
        v.define("rare", "...", "x")
        popular = v.define("popular", "...", "x")
        for _ in range(5):
            v.define("popular", "...", "x")  # updates → higher usage
        terms = v.terms()
        assert terms[0].term == "popular"

    def test_related_terms(self):
        v = Vocabulary()
        v.define("vessel", "...", "fleet", related_terms=["agent", "ship"])
        t = v.lookup("vessel")
        assert "agent" in t.related_terms


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------
class TestLexicon:
    def test_add_and_get(self):
        lex = Lexicon()
        wt = lex.add("hello", weight=0.8)
        assert isinstance(wt, WeightedTerm)
        assert lex.get("hello").weight == 0.8

    def test_case_insensitive(self):
        lex = Lexicon()
        lex.add("Hello")
        assert "hello" in lex
        assert lex.get("HELLO") is not None

    def test_synonyms(self):
        lex = Lexicon()
        lex.add("vessel")
        lex.add("ship")
        lex.add_synonym("vessel", "ship")
        assert "ship" in lex.synonyms("vessel")
        assert "vessel" in lex.synonyms("ship")

    def test_antonyms(self):
        lex = Lexicon()
        lex.add("fast")
        lex.add("slow")
        lex.add_antonym("fast", "slow")
        assert "slow" in lex.antonyms("fast")
        assert "fast" in lex.antonyms("slow")

    def test_resolve_picks_highest_weight(self):
        lex = Lexicon()
        lex.add("ship", weight=0.9)
        lex.add("vessel", weight=0.5)
        lex.add_synonym("ship", "vessel")
        assert lex.resolve("vessel") == "ship"

    def test_decay_all(self):
        lex = Lexicon()
        lex.add("term", weight=1.0)
        lex.decay_all(factor=0.5)
        assert lex.get("term").weight == 0.5

    def test_boost(self):
        lex = Lexicon()
        lex.add("term", weight=0.5)
        lex.boost_term("term", 0.3)
        assert lex.get("term").weight == 0.8

    def test_top(self):
        lex = Lexicon()
        lex.add("a", weight=0.3)
        lex.add("b", weight=0.9)
        lex.add("c", weight=0.6)
        assert [t.term for t in lex.top(2)] == ["b", "c"]

    def test_search(self):
        lex = Lexicon()
        lex.add("network", weight=0.7)
        lex.add("net", weight=0.5)
        assert len(lex.search("net")) == 2

    def test_remove_cleans_refs(self):
        lex = Lexicon()
        lex.add("a")
        lex.add("b")
        lex.add_synonym("a", "b")
        lex.remove("b")
        assert "b" not in lex.synonyms("a")

    def test_json_roundtrip(self):
        lex = Lexicon(name="test")
        lex.add("ship", weight=0.9)
        lex.add("vessel", weight=0.5)
        lex.add_synonym("ship", "vessel")
        lex.add_antonym("ship", "anchor")
        data = lex.to_json()
        lex2 = Lexicon.from_json(data)
        assert lex2.name == "test"
        assert len(lex2) == 2
        assert "vessel" in lex2.synonyms("ship")

    def test_len_iter(self):
        lex = Lexicon()
        lex.add("a")
        lex.add("b")
        assert len(lex) == 2
        terms = {t.term for t in lex}
        assert terms == {"a", "b"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class TestParser:
    def _vocab(self) -> Vocabulary:
        v = Vocabulary()
        v.define("vessel", "An autonomous agent", "fleet", related_terms=["agent"])
        v.define("signal", "Communication packet", "comms")
        v.define("anchor", "Station-keeping node", "fleet")
        return v

    def test_exact_match(self):
        p = CommandParser(self._vocab())
        r = p.parse("send signal to vessel")
        assert any(t.term == "signal" for t in r.matched_terms)
        assert any(t.term == "vessel" for t in r.matched_terms)

    def test_related_term_match(self):
        p = CommandParser(self._vocab())
        r = p.parse("deploy agent")
        assert any(t.term == "vessel" for t in r.matched_terms)

    def test_fuzzy_match(self):
        p = CommandParser(self._vocab(), fuzzy_threshold=0.5)
        r = p.parse("vessle")  # misspelling
        assert any(t.term == "vessel" for t, _ in r.fuzzy_matches)

    def test_unrecognized(self):
        p = CommandParser(self._vocab())
        r = p.parse("banana xyz")
        assert "banana" in r.unrecognized

    def test_stop_words_ignored(self):
        p = CommandParser(self._vocab())
        r = p.parse("the vessel is a signal")
        assert "the" not in r.unrecognized

    def test_best_match(self):
        p = CommandParser(self._vocab())
        r = p.parse("signal")
        assert r.best_match is not None
        assert r.best_match.term == "signal"

    def test_empty_input(self):
        p = CommandParser(self._vocab())
        r = p.parse("")
        assert len(r.matched_terms) == 0
        assert r.best_match is None


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------
class TestEncoder:
    def test_deterministic(self):
        enc = VocabularyEncoder(dimensions=32)
        v1 = enc.encode_term("vessel")
        v2 = enc.encode_term("vessel")
        assert v1 == v2

    def test_dimensions(self):
        enc = VocabularyEncoder(dimensions=128)
        assert len(enc.encode_term("test")) == 128

    def test_different_terms_differ(self):
        enc = VocabularyEncoder(dimensions=64)
        assert enc.encode_term("alpha") != enc.encode_term("beta")

    def test_weight_scaling(self):
        enc = VocabularyEncoder(dimensions=32)
        base = enc.encode("term", weight=1.0)
        heavy = enc.encode("term", weight=2.0)
        for b, h in zip(base.vector, heavy.vector):
            assert abs(h - 2 * b) < 1e-9

    def test_encode_vocabulary(self):
        v = Vocabulary()
        v.define("vessel", "A fleet agent", "fleet")
        v.define("signal", "A packet", "comms")
        enc = VocabularyEncoder()
        results = enc.encode_vocabulary(v)
        assert len(results) == 2
        assert all(len(r.vector) == 64 for r in results)

    def test_cosine_similarity(self):
        enc = VocabularyEncoder(dimensions=64)
        v1 = enc.encode_term("vessel")
        sim = enc.cosine_similarity(v1, v1)
        assert abs(sim - 1.0) < 1e-9

    def test_similarity_matrix(self):
        enc = VocabularyEncoder(dimensions=32)
        mat = enc.similarity_matrix(["vessel", "signal", "anchor"])
        assert len(mat) == 3
        assert mat[0][0] == 1.0
        assert mat[1][0] == mat[0][1]  # symmetric

    def test_bad_dimensions(self):
        try:
            VocabularyEncoder(dimensions=0)
            assert False, "Should raise"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Evolution
# ---------------------------------------------------------------------------
class TestEvolution:
    def test_record_and_query(self):
        tracker = EvolutionTracker()
        tracker.record("vessel", ChangeType.CREATED, new_value="fleet agent")
        tracker.record("vessel", ChangeType.UPDATED, new_value="updated def")
        assert len(tracker) == 2
        assert len(tracker.events(term="vessel")) == 2
        assert len(tracker.events(change_type=ChangeType.CREATED)) == 1

    def test_time_filtering(self):
        tracker = EvolutionTracker()
        now = time.time()
        tracker.record("old", ChangeType.CREATED)
        tracker.record("new", ChangeType.CREATED)
        events = tracker.events(since=now - 1)
        assert len(events) >= 1

    def test_summary(self):
        tracker = EvolutionTracker()
        tracker.record("a", ChangeType.CREATED)
        tracker.record("b", ChangeType.CREATED)
        tracker.record("a", ChangeType.UPDATED)
        s = tracker.summary()
        assert s["created"] == 2
        assert s["updated"] == 1

    def test_json_roundtrip(self):
        tracker = EvolutionTracker()
        tracker.record("vessel", ChangeType.CREATED, agent_id="a1", new_value="def")
        data = tracker.to_json()
        t2 = EvolutionTracker.from_json(data)
        assert len(t2) == 1
        assert t2.events()[0].term == "vessel"

    def test_from_vocabulary(self):
        v = Vocabulary()
        v.define("vessel", "A fleet agent", "fleet", agent_id="a1")
        v.define("signal", "A packet", "comms")
        tracker = EvolutionTracker.from_vocabulary(v)
        assert len(tracker) >= 2
        created = tracker.events(change_type=ChangeType.CREATED)
        assert len(created) == 2

    def test_limit(self):
        tracker = EvolutionTracker()
        for i in range(50):
            tracker.record(f"term-{i}", ChangeType.CREATED)
        assert len(tracker.events(limit=10)) == 10

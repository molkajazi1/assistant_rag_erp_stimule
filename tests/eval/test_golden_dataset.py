"""Data-validation tests for the golden dataset (DevRoadmap Phase 3).

Not unit or integration tests: they check the answer key itself, since every
benchmark score from Phase 4 on is only as trustworthy as this file.
"""

import json
from pathlib import Path

import pytest

from erp_rag.ingestion.loaders import load_records

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_dataset" / "qa_pairs.jsonl"
REQUIRED_FIELDS = {
    "id",
    "query_type",
    "question",
    "expected_answer",
    "expected_source_ids",
    "ambiguous",  # several records match the question as phrased (see test_golden_answers.py)
}
QUERY_TYPES = {"lookup", "filter", "aggregation", "multi-hop"}
MIN_ENTRIES = 15  # seed set size floor; Phase 9 grows it to 75-150


@pytest.fixture(scope="module")
def entries():
    lines = GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_golden_dataset_has_enough_entries(entries):
    assert len(entries) >= MIN_ENTRIES


def test_every_entry_has_exactly_the_required_fields(entries):
    for entry in entries:
        assert set(entry) == REQUIRED_FIELDS, entry.get("id")


def test_every_entry_has_non_empty_question_answer_and_sources(entries):
    for entry in entries:
        assert entry["question"].strip(), entry["id"]
        assert entry["expected_answer"].strip(), entry["id"]
        assert entry["expected_source_ids"], entry["id"]
        assert isinstance(entry["ambiguous"], bool), entry["id"]


def test_ids_are_unique(entries):
    ids = [entry["id"] for entry in entries]

    assert len(ids) == len(set(ids))


def test_query_types_are_valid_and_all_four_are_covered(entries):
    types = {entry["query_type"] for entry in entries}

    assert types == QUERY_TYPES


def test_every_expected_source_id_exists_in_the_corpus(entries):
    """A source id that doesn't exist (typo, or a corpus change since the entry was
    written) would silently score every retriever as wrong on that question."""
    corpus_ids = {record.id for record in load_records()}

    for entry in entries:
        missing = set(entry["expected_source_ids"]) - corpus_ids
        assert not missing, f"{entry['id']}: unknown source ids {sorted(missing)}"

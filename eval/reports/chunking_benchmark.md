# Chunking strategy benchmark

Status: not started — pending golden dataset (see ARCHITECTURE.md §4a).

## Objective

Determine which chunking strategy gives the best retrieval quality on the golden dataset, holding embedding model, retrieval config, and reranker fixed.

## Candidates

1. Fixed-size token chunking (baseline)
2. Record-level chunking (one chunk per invoice/order/stock item)
3. Hierarchical chunking (header/summary + line-item chunks)
4. Semantic/embedding-breakpoint chunking (free-text fields only)

See ARCHITECTURE.md §4 for the rationale behind this shortlist.

## Method

- Same corpus, same embedding model, same retrieval config (hybrid dense+BM25, RRF), same reranker for every candidate — chunking strategy is the only variable.
- Each candidate indexed separately.
- Evaluated against the full golden dataset (`eval/golden_dataset/qa_pairs.jsonl`).

## Metrics

- RAGAS: context precision, context recall
- Retrieval latency
- Index size / chunk count

## Results

_Not yet run._

| Strategy | Context precision | Context recall | Latency (p50) | Chunk count |
|---|---|---|---|---|
| Fixed-size | — | — | — | — |
| Record-level | — | — | — | — |
| Hierarchical | — | — | — | — |
| Semantic (free-text fields) | — | — | — | — |

## Possible future ablation: overlap on fixed-size chunking

`fixed_size_chunk()` (`src/erp_rag/ingestion/chunking.py`) deliberately has no overlap between chunks — kept maximally naive so the baseline/strawman comparison against the other strategies is as unambiguous as possible (no record-awareness of any kind). Overlapping chunks (consecutive chunks sharing some words at their boundary) is a well-known, still-fully-naive refinement real systems commonly use (e.g. LangChain's default text splitter ships with overlap) to soften the "context lost at a hard boundary" problem, without needing any record structure awareness.

Worth trying as a follow-up *if* record-level chunking (or the others) doesn't win by much — would tell us whether a cheap, structure-agnostic fix closes most of the gap, or whether genuinely respecting record boundaries is what actually matters. Not implemented now, on purpose — see DevRoadmap.md Phase 2 discussion.

## Decision

_Not yet decided._

**Rationale:**

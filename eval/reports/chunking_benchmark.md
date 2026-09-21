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

## Decision

_Not yet decided._

**Rationale:**

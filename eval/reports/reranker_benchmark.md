# Reranker benchmark

Status: not started — pending golden dataset (see ARCHITECTURE.md §4a).

## Objective

Determine whether cross-encoder reranking is worth its added latency, and which reranker model gives the best retrieval quality on the golden dataset, holding chunking strategy, embedding model, and retrieval config fixed.

## Candidates

1. No reranker (baseline — hybrid retrieval output used as-is)
2. `cross-encoder/ms-marco-MiniLM-L-6-v2`
3. `cross-encoder/ms-marco-MiniLM-L-12-v2`
4. `BAAI/bge-reranker-base`

## Method

- Same corpus, same (winning) chunking strategy, same (winning) embedding model, same retrieval config for every candidate — reranker is the only variable.
- Reranking applied to the same top-k hybrid retrieval results for every candidate.
- Evaluated against the full golden dataset (`eval/golden_dataset/qa_pairs.jsonl`).

## Metrics

- RAGAS: context precision, context recall
- End-to-end answer quality (faithfulness, answer relevancy) — reranking's effect should show up downstream, not just in retrieval metrics
- Added latency vs. no-reranker baseline

## Results

_Not yet run._

| Reranker | Context precision | Context recall | Faithfulness | Answer relevancy | Added latency |
|---|---|---|---|---|---|
| None (baseline) | — | — | — | — | — |
| ms-marco-MiniLM-L-6-v2 | — | — | — | — | — |
| ms-marco-MiniLM-L-12-v2 | — | — | — | — | — |
| bge-reranker-base | — | — | — | — | — |

## Decision

_Not yet decided._

**Rationale:**

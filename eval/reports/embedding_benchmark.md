# Embedding model benchmark

Status: not started — pending golden dataset (see ARCHITECTURE.md §4a).

## Objective

Determine which local embedding model gives the best retrieval quality on the golden dataset, holding chunking strategy, retrieval config, and reranker fixed.

## Candidates

1. `BAAI/bge-small-en-v1.5` (384-dim)
2. `BAAI/bge-base-en-v1.5` (768-dim)
3. `intfloat/e5-small-v2`
4. `sentence-transformers/all-MiniLM-L6-v2`

All local/CPU, English-only, no API key required — consistent with the project's local-retrieval deployment decision (ARCHITECTURE.md §2).

## Method

- Same corpus, same (winning) chunking strategy, same retrieval config, same reranker for every candidate — embedding model is the only variable.
- Each candidate indexed separately in Chroma.
- Evaluated against the full golden dataset (`eval/golden_dataset/qa_pairs.jsonl`).

## Metrics

- RAGAS: context precision, context recall
- Embedding + retrieval latency
- Index build time / index size

## Results

_Not yet run._

| Model | Dim | Context precision | Context recall | Latency (p50) | Index size |
|---|---|---|---|---|---|
| bge-small-en-v1.5 | 384 | — | — | — | — |
| bge-base-en-v1.5 | 768 | — | — | — | — |
| e5-small-v2 | — | — | — | — | — |
| all-MiniLM-L6-v2 | 384 | — | — | — | — |

## Decision

_Not yet decided._

**Rationale:**

# Chunking strategy benchmark

Status: strategies implemented and spot-checked (Phase 2, 2026-10-26); benchmark not run yet — pending golden dataset (Phase 3) and indexes (Phase 4). See "Implementation notes" below.

## Objective

Determine which chunking strategy gives the best retrieval quality on the golden dataset, holding embedding model, retrieval config, and reranker fixed.

## Candidates

1. Fixed-size token chunking (baseline)
2. Record-level chunking (one chunk per invoice/order/stock item)
3. Hierarchical chunking (header/summary + line-item chunks)

See ARCHITECTURE.md §4 for the rationale behind this shortlist. A fourth candidate, semantic/embedding-breakpoint chunking, was considered and deliberately excluded (not benchmarked, not just skipped) — see ARCHITECTURE.md §4 for why: the technique targets topic drift in prose, and this corpus has no topics, only facts connected by explicit foreign keys already more reliable than inferred embedding similarity.

## Implementation notes (Phase 2)

What exists, so the benchmark in Phase 4 has a clear starting point:

- **Code:** `src/erp_rag/ingestion/chunking.py` — one pure function per strategy (`list[Record] -> list[Chunk]`), selectable by name via `CHUNKING_STRATEGIES` / `get_chunking_strategy()`. `src/erp_rag/ingestion/loaders.py` — `load_records()` reads `data/raw/` back into validated Pydantic records; `load_chunks(strategy)` loads and chunks in one call.
- **Tests:** per-strategy unit tests (boundaries, counts, rendered fields, orphan line items), a registry test that each strategy's name matches the `strategy` tag on its chunks, and a loader round-trip test (committed CSVs == fresh generator build).

Chunk counts on the full corpus (1,369 records, after the order-lifecycle fix below):

| Strategy | Chunks | Shape |
|---|---|---|
| Fixed-size | 54 | Pydantic `str()` dumps of records, concatenated and cut every 200 words; 9 to 41 records per chunk, some chunks mix entity types |
| Record-level | 1,369 | One templated sentence per record, customer/product IDs resolved to names |
| Hierarchical | 1,369 | Same count as record-level (one chunk per record) but different content: order chunks list their line-item IDs, line-item chunks carry the order's customer and date and link to the order in `source_ids` |

**Spot check (by hand, 2026-10-26, on the corpus *before* the order-lifecycle fix — the IDs below refer to that version):** sampled one customer → order → line items → invoice chain (`CUST-0041`, `ORD-0001`, `OLI-0001..0003`, `INV-0001`), one unpaid invoice (`INV-0026`), and one fixed-size chunk. Text is readable, IDs and names resolve correctly, and the numbers are consistent (`INV-0001` amount $1,214.51 = 3 × $232.52 + $228.97 + $287.98; `INV-0026` is `pending` with a due date one day after the reference date). Fixed-size chunks start and end mid-record, as intended for the baseline.

Findings to resolve or caveat **before** the benchmark is run:

1. **Fixed-size differs from the others in two ways, not one.** It changes the boundaries (ignores records) *and* the text format (raw `id='CUST-0001' name=...` dumps, not the readable template). A gap between fixed-size and record-level would mix both effects. ARCHITECTURE.md §4 describes it as chunking "raw exports", so this matches the spec, but the report must say so, or a variant cutting the *templated* text by word count should be added to isolate boundaries alone.
2. **Words, not tokens.** ARCHITECTURE.md §4 says "fixed-size token chunking"; the code splits on whitespace words (`DEFAULT_CHUNK_SIZE = 200`). Fine for a baseline, but the doc and the code should say the same thing.
3. **Invoice chunks don't name the customer.** An invoice chunk only says "for order ORD-0001"; the customer is two hops away (invoice → order → customer). A question like "Mark Lloyd's unpaid invoices" can't match an invoice chunk by name in either record-level or hierarchical. This could be fixed in the template (resolve the customer through the order) or left for the agent's multi-hop retrieval (Phase 7) — a design decision, and one that directly affects the benchmark numbers.
4. ~~**Order status and invoice status can contradict each other.**~~ **Resolved 2026-10-26.** Order status was random and independent of invoicing (63 cancelled orders had invoices, 15 payments were dated after the reference date). Order status now follows the order's age on `as_of` (pending → confirmed → shipped → delivered, plus 8% cancelled), and only shipped/delivered orders are invoiced, with no invoice or payment dated after `as_of`. The corpus changed once (264 invoices instead of 300), before any golden answer existed.
5. *(Cosmetic)* Product prices are uniform 5 to 500 regardless of category (a ream of printer paper at $221.23), and addresses pair a US-style street with a random country. Harmless for retrieval; worth knowing when reading answers.

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

## Possible future ablation: overlap on fixed-size chunking

`fixed_size_chunk()` (`src/erp_rag/ingestion/chunking.py`) deliberately has no overlap between chunks — kept maximally naive so the baseline/strawman comparison against the other strategies is as unambiguous as possible (no record-awareness of any kind). Overlapping chunks (consecutive chunks sharing some words at their boundary) is a well-known, still-fully-naive refinement real systems commonly use (e.g. LangChain's default text splitter ships with overlap) to soften the "context lost at a hard boundary" problem, without needing any record structure awareness.

Worth trying as a follow-up *if* record-level chunking (or the others) doesn't win by much — would tell us whether a cheap, structure-agnostic fix closes most of the gap, or whether genuinely respecting record boundaries is what actually matters. Not implemented now, on purpose — see DevRoadmap.md Phase 2 discussion.

## Decision

_Not yet decided._

**Rationale:**

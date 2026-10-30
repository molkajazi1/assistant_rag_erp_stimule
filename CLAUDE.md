# CLAUDE.md

Context for Claude Code sessions working on this repo.

## What this project is

A portfolio project: a RAG assistant over a synthetic ERP corpus (invoices, stock, orders) generated with Python/Faker — no real ERP system involved. The point of the project is not "a working RAG" alone; it's a working RAG whose reliability is backed by numbers. Every feature decision should be checkable against: **does this let us quantify something in the before/after report?**

Two fused halves make up "done":
1. An advanced RAG pipeline — compared chunking strategies, hybrid search, cross-encoder reranking, and an agentic retrieval layer (LangGraph).
2. A rigorous evaluation layer — golden dataset, RAGAS automated metrics, LLM-as-judge, Langfuse observability, red teaming, a guardrail, and a quantified before/after report.

Full architecture and the rationale behind every tech choice is in [ARCHITECTURE.md](ARCHITECTURE.md) — read it before proposing a different vector store, embedding model, or framework. If you think a decision there is wrong, say so and why; don't silently substitute something else.

## Locked decisions (see ARCHITECTURE.md for full rationale)

- **Deployment**: hybrid — local retrieval (free, reproducible), cloud generation (Claude via `langchain-anthropic`).
- **Advanced architecture**: Agentic RAG via LangGraph (plan → retrieve → sufficiency check → re-plan or answer).
- **Corpus language**: English only.
- **Vector store**: Chroma (local, metadata filtering).
- **Sparse index**: `rank_bm25`, fused with dense via RRF.
- **Embeddings & reranker**: NOT preselected — chosen by benchmark, same as chunking. See "Benchmark-then-decide" below before hardcoding a model name anywhere.
- **Observability**: Langfuse (self-hosted via docker-compose preferred over cloud tier).
- **Eval metrics**: RAGAS + a separate LLM-as-judge prompt (Claude, distinct rubric from the generator).
- **Dependency management**: Poetry (project owner's choice — already knows it well), not uv or plain pip.

Don't relitigate these without a concrete reason surfaced during implementation (e.g. an eval number that contradicts the assumption). If one changes, update ARCHITECTURE.md's decision table in the same change.

## Working conventions

- **Benchmark-then-decide, not preselect.** Chunking strategy, embedding model, and reranker model are all decided by running candidates through the golden dataset and comparing — never by picking the "obviously good" option upfront. Each has its own results file: `eval/reports/chunking_benchmark.md`, `eval/reports/embedding_benchmark.md`, `eval/reports/reranker_benchmark.md` (currently placeholders — fill them in as each benchmark is actually run, don't skip to a decision without numbers in the table). See ARCHITECTURE.md §4a for the candidate shortlists.
- **Everything is an ablation.** When implementing chunking strategies, retrieval configs, or guardrail toggles, keep them swappable via config rather than hardcoded, so `scripts/run_eval.py` can run the same golden dataset against each variant and produce a real comparison table.
- **The golden dataset comes before the agent's tool design.** Draft `eval/golden_dataset/qa_pairs.jsonl` with a query-type taxonomy (lookup / filter / aggregation / multi-hop) early — the agent's tools should be designed to answer real eval questions, not the other way around.
- **LLM provider is abstracted**, not hardcoded to Anthropic — `src/erp_rag/generation/` should make swapping in OpenAI a config change, both for the generator (possible ablation) and to avoid the judge and generator being inseparable.
- **Guardrails are custom-built**, not a framework (Guardrails AI / NeMo Guardrails) — this is intentional, so the mechanism is transparent and its effect shows up directly in the before/after report. Don't swap in a framework without discussing it first.
- **No real ERP data, ever.** All data comes from `src/erp_rag/corpus/` Faker generators. Don't introduce real customer/company names or actual invoice data as "test fixtures."

## Claude Code usage tracing

The README commits to documenting how Claude Code was used to build this project. When you do substantial work in a session (implementing a pipeline stage, writing the eval harness, debugging a chunking strategy), that's worth a line in the README's Claude Code usage log — check whether that section exists and whether this session's work belongs in it before ending a significant task.

## Project structure

See ARCHITECTURE.md §5 for the full layout. Key paths:
- `src/erp_rag/` — pipeline code, organized by stage (corpus, ingestion, indexing, retrieval, agent, generation, guardrails, observability).
- `eval/` — golden dataset, RAGAS/LLM-judge scripts, red team prompts, generated reports.
- `scripts/` — entry points (`build_corpus.py`, `build_index.py`, `run_eval.py`).

## Current status

Phases 0 (environment, CI), 1 (synthetic corpus), 2 (chunking: three strategies selectable by name, `loaders.py`) and 3 (seed golden dataset: 20 approved, truth-tested questions in `eval/golden_dataset/qa_pairs.jsonl`) are complete. Next is Phase 4 (indexing, hybrid retrieval, chunking benchmark). Progress is tracked with Status lines and checkboxes in DevRoadmap.md; open chunking findings are in `eval/reports/chunking_benchmark.md`.

Golden answers follow the **clarify-first rule** (ARCHITECTURE.md §4c): an ambiguous question gets a short explanation plus a clarifying question with at most 3 example options, then a second turn. Every golden entry must have a verifier in `tests/eval/test_golden_answers.py` that recomputes its answer from the corpus; don't hand-write an expected answer without one. Check git log / project structure for what's actually been built before trusting this note, which can go stale.

The corpus is deterministic by seed **and** by date: generators take an `as_of` date defaulting to `CORPUS_REFERENCE_DATE` and must never read the real clock (ARCHITECTURE.md §4b). Don't reintroduce `datetime.now()`, `date.today()` or Faker's `"today"` anywhere in the pipeline.

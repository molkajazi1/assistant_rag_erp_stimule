# RAG Assistant on Simulated ERP Exports

A RAG assistant that answers natural language questions about simulated ERP documents (invoices, stock, orders). Synthetic corpus generated with Python/Faker, no real ERP access needed.

A measurable project: beyond the RAG pipeline itself (chunking, hybrid search, reranking, advanced architecture), it includes a quantified evaluation (golden dataset, automated metrics, LLM-as-judge, observability, red teaming, guardrails).

## Status

In development. Phases 0 (environment, CI), 1 (synthetic corpus), 2 (chunking strategies) and 3 (seed golden dataset, 20 truth-tested questions) are complete; Phase 4 (indexing, hybrid retrieval, chunking benchmark) is next. See [DevRoadmap.md](DevRoadmap.md) for the full phased plan.

## Stack

- **Retrieval**: Chroma (dense) + BM25 (sparse), fused with RRF, cross-encoder reranking. Embedding and reranker models are chosen by benchmark, not preselected — see `eval/reports/`.
- **Advanced architecture**: Agentic RAG orchestrated with LangGraph.
- **Generation**: Claude (Anthropic API), via a swappable provider abstraction.
- **Evaluation**: golden dataset, RAGAS automated metrics, LLM-as-judge, red teaming, custom guardrails.
- **Observability**: Langfuse.
- **Tooling**: Python, Poetry for dependency management.

Full rationale for each choice: [ARCHITECTURE.md](ARCHITECTURE.md).

## Claude Code usage

This project is built in collaboration with [Claude Code](https://claude.com/claude-code). Design decisions stay with the project owner; Claude Code is used to explain options, implement them, and check the result against the repo (tests, lint, data). Log of what was done, per session:

| Date | Work | Notable decisions / findings |
|---|---|---|
| 2026-09-21 / 09-23 | Pre-development: architecture, stack, and phased roadmap ([ARCHITECTURE.md](ARCHITECTURE.md), [DevRoadmap.md](DevRoadmap.md)); Poetry environment with ruff and pytest | Benchmark-then-decide for chunking, embedding and reranker instead of preselecting models |
| 2026-10-12 | Phase 0 CI kata: first GitHub Actions workflow built step by step (checkout, Python, Poetry, ruff); Pydantic schema for the corpus | `src` layout and `requires-python` fixes surfaced by the first CI runs |
| 2026-10-22 | Phase 1: seeded Faker generators for customers, products, orders, line items and invoices, with unit tests; corpus snapshot committed. Phase 2: fixed-size, record-level and hierarchical chunking with tests. CI split into parallel lint and test jobs | Semantic chunking dropped on principle: FK-linked tabular data has no topic drift to detect (ARCHITECTURE.md §4) |
| 2026-10-26 | Phase 0/1 leftovers: `ruff format --check` in CI, `workflow_dispatch`, CI pinned to Python 3.11, `.env.example`. Found and fixed a clock dependency in the corpus generators | The corpus changed depending on the day it was built (Faker `"today"`, `datetime.now()`), which would have silently invalidated golden dataset answers. Fixed with a fixed `CORPUS_REFERENCE_DATE` / `as_of` input and a freezegun test; rebuild verified byte-identical. Led to ARCHITECTURE.md §4b: frozen data for evaluation, live data and the real date for the product |
| 2026-10-26 (cont.) | Phase 2 completed: `loaders.py` (CSV back to validated records), strategy selection by name, manual spot check. Phase 1 follow-up: consistent order lifecycle. Phase 3 started: 20-question golden draft with schema and truth tests | Spot check found order and invoice statuses contradicting each other (63 cancelled orders invoiced), fixed before writing any golden answer. Equal split across query types; questions rewritten in natural language ("Warner sticky notes") at the owner's request. Truth tests verified by planting wrong answers, which exposed and fixed a too-weak check |
| 2026-10-30 | Clarify-first rule for ambiguous questions applied to the golden dataset (2-turn entries) and documented (ARCHITECTURE.md §4c); golden dataset approved, Phase 3 closed; docs resynced with the project state; architecture diagram translated to English | Owner's rule: for an ambiguous question, explain briefly and ask a clarifying question with a few example options *before* retrieving details, which keeps retrieved context small (2 candidate records instead of 18 for "Lee") |

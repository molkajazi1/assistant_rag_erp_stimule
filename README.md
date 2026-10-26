# RAG Assistant on Simulated ERP Exports

A RAG assistant that answers natural language questions about simulated ERP documents (invoices, stock, orders). Synthetic corpus generated with Python/Faker, no real ERP access needed.

A measurable project: beyond the RAG pipeline itself (chunking, hybrid search, reranking, advanced architecture), it includes a quantified evaluation (golden dataset, automated metrics, LLM-as-judge, observability, red teaming, guardrails).

## Status

In development. Phases 0 (environment, CI) and 1 (synthetic corpus) are complete; Phase 2 (chunking strategies) is in progress. See [DevRoadmap.md](DevRoadmap.md) for the full phased plan.

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

# RAG Assistant on Simulated ERP Exports

A RAG assistant that answers natural language questions about simulated ERP documents (invoices, stock, orders). Synthetic corpus generated with Python/Faker, no real ERP access needed.

A measurable project: beyond the RAG pipeline itself (chunking, hybrid search, reranking, advanced architecture), it includes a quantified evaluation (golden dataset, automated metrics, LLM-as-judge, observability, red teaming, guardrails).

## Status

Pre-development complete — architecture and stack are locked (see [ARCHITECTURE.md](ARCHITECTURE.md)). Implementation has not started.

## Stack

- **Retrieval**: Chroma (dense) + BM25 (sparse), fused with RRF, cross-encoder reranking. Embedding and reranker models are chosen by benchmark, not preselected — see `eval/reports/`.
- **Advanced architecture**: Agentic RAG orchestrated with LangGraph.
- **Generation**: Claude (Anthropic API), via a swappable provider abstraction.
- **Evaluation**: golden dataset, RAGAS automated metrics, LLM-as-judge, red teaming, custom guardrails.
- **Observability**: Langfuse.
- **Tooling**: Python, Poetry for dependency management.

Full rationale for each choice: [ARCHITECTURE.md](ARCHITECTURE.md).

## Claude Code usage

This project's pre-development phase (architecture and stack decisions) was done in collaboration with [Claude Code](https://claude.com/claude-code). This section will be kept up to date as implementation proceeds.

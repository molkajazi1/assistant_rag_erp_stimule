# Architecture

Status: decisions locked; implementation in progress (Phases 0-3 done, Phase 4 next, see DevRoadmap.md). Sections §4b and §4c were added during implementation. Revisit only if implementation reveals a wrong assumption below — update this file when that happens, don't let it drift out of sync with the code.

## 1. Goals recap

Two fused objectives, both required for "done":

1. An advanced RAG pipeline over a synthetic ERP corpus (invoices, stock, orders), with compared chunking strategies, hybrid search, a cross-encoder reranker, and an agentic retrieval layer.
2. A rigorous evaluation layer: golden dataset, automated metrics + LLM-as-judge, an observability tool wired in, basic red teaming, a guardrail, and a quantified before/after report.

A result without numbers behind it does not satisfy this project's definition of done — every architectural choice below exists to produce a comparison, not just a working demo.

## 2. Decisions

| Area | Decision | Why |
|---|---|---|
| Deployment model | Hybrid: local retrieval, cloud generation | Free/reproducible retrieval side (anyone can clone and run it without a cloud embedding bill); paid API only for the LLM calls that actually need top generation quality (answer synthesis, LLM-as-judge). |
| Advanced architecture | Agentic RAG | ERP questions are naturally multi-entity / multi-hop ("which customers had late invoices last quarter and what did they order") — a single retrieve-then-generate pass underperforms here. An LLM-driven planner that decomposes into sub-queries and picks tools (structured filter vs. semantic search vs. aggregation) is the right fit. |
| Orchestration | LangGraph | Agentic RAG needs an explicit state machine (plan → retrieve → check sufficiency → re-plan or answer). LangGraph gives that without hiding the control flow the way a fully implicit agent framework would; LangChain components (loaders, retrievers) are used underneath where they save real work, not as a black box. |
| Corpus / query language | English only | Simplifies embedding model choice (mature English-optimized models) and widens the audience for the portfolio artifact. |
| Vector store | Chroma | Local, free, persists to disk, and has real metadata filtering — required here because ERP queries are filter-heavy ("invoices for customer X after March"), not pure semantic search. FAISS is a bare index with no filtering/persistence layer; Pinecone adds cost and a network dependency that stops reviewers from just cloning and running the repo. |
| Sparse index (hybrid search) | `rank_bm25` (BM25Okapi), in-process | No server to stand up, trivial to keep in sync with the same chunk store as Chroma. Dense + sparse results fused with Reciprocal Rank Fusion (RRF). |
| Embedding model | Benchmarked, not preselected — see [eval/reports/embedding_benchmark.md](eval/reports/embedding_benchmark.md) | Candidates: `BAAI/bge-small-en-v1.5`, `BAAI/bge-base-en-v1.5`, `intfloat/e5-small-v2`, `sentence-transformers/all-MiniLM-L6-v2`. All local/CPU/English, so the choice is decided purely by retrieval quality (context precision/recall on the golden dataset) vs. latency and index size — the same way chunking is decided (§4). |
| Reranker | Benchmarked, not preselected — see [eval/reports/reranker_benchmark.md](eval/reports/reranker_benchmark.md) | Candidates: `cross-encoder/ms-marco-MiniLM-L-6-v2`, `cross-encoder/ms-marco-MiniLM-L-12-v2`, `BAAI/bge-reranker-base`, plus a **no-reranker baseline** to quantify whether reranking is worth its added latency at all. |
| Generation LLM | Claude (Anthropic API), via `langchain-anthropic` | Cloud generation per the hybrid decision. Routed through a thin provider abstraction (not hardcoded) so swapping in OpenAI for an ablation ("does the generator model change the numbers?") is a config change, not a rewrite. |
| LLM-as-judge | Claude, separate prompt/config from the generator | Using the same provider is fine — the judge is a distinct prompt with its own rubric, not the same call reused. Keeping it swappable also guards against self-preference bias if that becomes a concern later. |
| Automated metrics | RAGAS (faithfulness, answer relevancy, context precision, context recall) | Standard, well-documented library for exactly the metrics this project needs to quantify chunking/retrieval/reranking changes. |
| Observability | Langfuse (self-hosted via `docker-compose`, or free cloud tier) | Native LangChain/LangGraph integration matters here since the agent is built on LangGraph — traces of the plan → retrieve → re-plan loop are the debugging tool, not a nice-to-have. Langfuse also gives prompt versioning and dataset management, which doubles as the home for the golden dataset. Arize Phoenix is an equally valid swap (stronger embedding-drift visualization) if Langfuse's setup proves friction-heavy. |
| Guardrails | Custom, not a framework | Two lightweight checks: (1) input — regex + small classifier prompt to catch prompt injection and requests for another customer's data (multi-tenant leakage is the realistic ERP risk, not generic toxicity); (2) output — a groundedness check against retrieved context, refusing/"I don't know"-ing ungrounded answers. Kept custom rather than pulling in Guardrails AI / NeMo Guardrails so the mechanism is transparent and directly tied to the eval report's before/after numbers. |
| Red teaming | Small curated adversarial set + LLM-judge grading | Prompt injection attempts, cross-customer data exfiltration attempts, out-of-corpus questions (hallucination bait). Not a full `garak` run — scoped to what's realistic for a single-tenant-per-query ERP assistant. |
| Dependency management | Poetry | Already mastered by the project owner — no tooling-learning overhead on top of everything else. Poetry 2.0+ supports standard PEP 621 `pyproject.toml`, so the old "non-standard format" objection no longer applies. |

## 3. Pipeline

```
Faker corpus generation (invoices, stock, orders → CSV/JSON)
        │
        ▼
Chunking  ──────────────────────────────────────────┐
  (strategies compared, see §4)                      │  compared empirically,
        │                                             │  not just implemented
        ▼                                             │
Embedding (model chosen via benchmark, §4a)           │
        │                                             │
        ▼                                             │
Indexing                                              │
  ├─ Chroma (dense vectors + metadata filters)        │
  └─ BM25 (rank_bm25, sparse)                          │
        │                                             │
        ▼                                             │
Agentic retrieval (LangGraph)                         │
  plan → {hybrid retrieve (RRF fuse dense+sparse),    │
          structured filter, aggregate} → sufficiency │
          check → re-plan or proceed                  │
        │                                             │
        ▼                                             │
Cross-encoder rerank (model chosen via benchmark, §4a)│
        │                                             │
        ▼                                             │
Output guardrail (groundedness check)                 │
        │                                             │
        ▼                                             │
Generation (Claude via langchain-anthropic, cited)    │
        │                                             │
        ▼                                             │
Input guardrail sits before the planner; Langfuse traces every stage above.
                                                       │
                                                       ▼
                                        Eval layer (RAGAS + LLM-judge + golden
                                        dataset + red team set) → quantified
                                        before/after report
```

The eval layer wraps the whole pipeline rather than bolting onto the end: every chunking strategy, every retrieval config (dense-only vs. hybrid, reranked vs. not), and every guardrail toggle gets run through the same golden dataset so the before/after report is a real ablation table, not a single anecdote.

## 4. Chunking strategies to compare

This is structured tabular ERP data, not prose, so the interesting comparison isn't the usual fixed-size-vs-semantic split:

1. **Fixed-size token chunking** — baseline/strawman, chunk raw exports by token count ignoring structure.
2. **Record-level chunking** — one chunk per invoice / order / stock item, rendered through a text template (e.g. "Invoice INV-1042 for customer Acme Corp, dated 2026-03-01, total $1,240, status: paid, line items: ..."). Expected winner for this domain — preserves the atomic unit a query is usually about.
3. **Hierarchical chunking** — header/summary chunk + separate line-item chunks, linked by ID, for documents with many line items where record-level chunks would get too large.

**Considered and deliberately dropped: semantic (embedding-breakpoint) chunking.** This technique's value is finding topic drift in flowing prose — our data has no topics, only discrete facts connected by explicit foreign keys. Giving it something to chunk would have meant inventing a free-text field (e.g. `Order.notes`) that doesn't otherwise belong in the schema, purely to justify the technique — forcing a feature to fit a pre-chosen method rather than the reverse. Since the FK relationships are already perfect, known structure, relying on inferred embedding similarity instead would be strictly worse than what strategies 2-3 already do by using that structure directly. Not benchmarked, on principle, not just skipped for time.

Each remaining strategy is indexed separately and run through the same golden dataset with the same retrieval/rerank config, isolating chunking as the only variable — that's the number that goes in the before/after report. Results and the final decision are recorded in [eval/reports/chunking_benchmark.md](eval/reports/chunking_benchmark.md).

## 4a. Benchmark-then-decide pattern

Chunking, embedding model, and reranker model are **all** decided this way, not preselected: shortlist candidates, run each through the same golden dataset holding everything else fixed, and record the result. This is deliberate — the project's value is the numbers behind the choices, not the choices themselves. Each stage gets its own report under `eval/reports/`, using a consistent template (objective, candidates, metrics, method, results table, decision + rationale):

- [eval/reports/chunking_benchmark.md](eval/reports/chunking_benchmark.md) — strategies in §4.
- [eval/reports/embedding_benchmark.md](eval/reports/embedding_benchmark.md) — candidates in the decision table (§2).
- [eval/reports/reranker_benchmark.md](eval/reports/reranker_benchmark.md) — candidates in the decision table (§2), including the no-reranker baseline.

These are placeholder files until each benchmark actually runs (the chunking report already holds the Phase 2 implementation notes) — they get filled in once the golden dataset and indices exist to actually run the comparisons. Don't skip straight to "pick the obvious-looking option" during implementation; the placeholder existing is a reminder to run the benchmark first.

## 4b. Time and data freshness: evaluation vs. the real product

Two different requirements that must not be confused:

- **Evaluation needs a frozen world.** The synthetic corpus is deterministic: same seed + same reference date → identical CSVs, on any day the build runs. The reference date (`CORPUS_REFERENCE_DATE`, 2026-10-22, the day the committed snapshot was generated) plays the role of "today" for the fictional company, so date-relative facts (order dates within "the last 12 months", invoice `overdue` status) don't drift with the calendar. Without it, golden dataset answers go stale on their own, and a benchmark delta mixes "the pipeline changed" with "the calendar moved" — the exact confound §4a exists to avoid.
- **The real product needs a live world.** Deployed against a real ERP there is no generator: records are created and updated constantly, and "today" is the real clock. The deterministic corpus is a measurement fixture, not a model of production behavior.

Design rules that follow from this:

1. **No hidden clock.** No pipeline component calls `datetime.now()` / `date.today()` directly. The current date is an explicit `as_of` input: the fixed reference date in evaluation, the real date in production. This applies to the corpus generator (Phase 1) and to the agent (Phase 7) — time-relative questions ("which invoices are overdue?") are resolved against `as_of`, never against a date frozen into the code.
2. **Time-dependent facts are derived at query time where possible.** A stored status like `overdue` is only true as of the moment it was written. In production it should be computed from `due_date`, `payment_date` and `as_of` (e.g. by the aggregation/filter tools), not trusted from the indexed chunk text, which goes stale as soon as the date moves. In the synthetic corpus the stored status is consistent with the reference date, so evaluation is unaffected.
3. **Indexes must be updatable, not only rebuildable.** Chunks keep their source record ID(s) as stable IDs, so a new or changed record can be upserted into Chroma without a full rebuild. `rank_bm25` has no incremental update, so for BM25 "update" means a rebuild from the chunk store — cheap at this corpus size. Full ERP sync is a product concern beyond the portfolio's core scope; Phase 14 demonstrates it with a simulated "live" mode, kept separate from the frozen evaluation corpus.

## 4c. Natural-language references and the clarify-first rule

Users mostly don't type IDs. They say "Warner sticky notes" (brand only partly given), "Lee" (a surname shared by two customers), or "the $12,636.26 invoice", and the assistant has to work out which records they mean. Two requirements follow, and the golden dataset tests both:

1. **Entity resolution.** The agent maps partial, natural references (name fragments, partial brand names, amounts, "latest order") to concrete record IDs before answering. IDs still work when the user gives them.
2. **Clarify first when the question is ambiguous or unclear.** When a reference matches several records (8 products are called "Aluminum Rod") or the request is too vague to answer precisely, the assistant does **not** retrieve and report on every match. It replies with:
   - a short **explanation** of why it can't answer yet ("I found 8 different products called Aluminum Rod, each from a different brand..."), then
   - a **clarifying question** offering a **few example options** (at most 3, e.g. "Which brand is it? For example, Hancock and Sons or Bryant Group."), never the full list unless the user explicitly asks for it.

   Only after the user's reply does it retrieve the detailed records and answer. **Why:** asking first keeps the retrieved context small and focused (2 candidate customers instead of 18 invoice/order chunks for "Lee"), avoids guessing, and matches how a person would handle the same question.

**In the golden dataset:** ambiguous entries carry `"ambiguous": true`. Their `expected_answer` is the explanation plus the clarifying question, and `expected_source_ids` holds only the candidate records needed to notice the ambiguity. A second turn records the user's reply (`follow_up`), the final answer (`follow_up_answer`) and the records it needs (`follow_up_source_ids`). These three fields are `null` on every other entry.

**When it's built:** the golden dataset specifies the behavior now (Phase 3). The agent implements it in Phase 7 (ambiguity detection plus a LangGraph interrupt that pauses for the user's reply), and the eval harness grades both turns in Phase 9.

## 5. Project structure

```
assistant-rag-erp-simule/
├── README.md
├── ARCHITECTURE.md
├── CLAUDE.md
├── pyproject.toml            # Poetry-managed
├── poetry.lock
├── .env.example
├── data/
│   ├── raw/                  # Faker-generated ERP exports
│   └── processed/            # chunked docs per strategy
├── src/
│   └── erp_rag/
│       ├── corpus/           # Faker generation (invoices, stock, orders)
│       ├── ingestion/        # chunking strategies, loaders
│       ├── indexing/         # embeddings, Chroma wrapper, BM25 index
│       ├── retrieval/        # hybrid retriever (RRF), reranker
│       ├── agent/            # LangGraph state machine, nodes, tools
│       ├── generation/       # LLM provider abstraction
│       ├── guardrails/       # input_guard.py, output_guard.py
│       └── observability/    # Langfuse tracing setup
├── eval/
│   ├── golden_dataset/       # qa_pairs.jsonl
│   ├── metrics/              # ragas_eval.py, llm_judge.py
│   ├── redteam/              # adversarial_prompts.jsonl
│   └── reports/              # chunking_benchmark.md, embedding_benchmark.md,
│                              # reranker_benchmark.md, + overall before/after report
├── notebooks/                # exploratory chunking/retrieval comparisons
├── tests/
└── scripts/
    ├── build_corpus.py
    ├── build_index.py
    └── run_eval.py
```

## 6. Open items to resolve during implementation

- ~~Exact golden dataset size and query-type taxonomy~~ **Settled for the seed set (Phase 3):** 20 entries, an equal 5 per type (lookup / filter / aggregation / multi-hop), plus an `ambiguous` flag for clarify-first entries (§4c). The full size (75-150) is set in Phase 9.
- Whether the BM25 index is rebuilt per chunking-strategy comparison or only for the final chosen strategy (rebuilding for all keeps the ablation fair; decide once corpus size is known).
- Langfuse self-host (docker-compose) vs. free cloud tier — self-host is more reproducible for reviewers, cloud tier is faster to set up. Default to self-host unless it proves to be friction during setup.
- How the "live" mode refreshes the indexes (§4b): what triggers it (on-demand API endpoint vs. schedule) and how new/changed records are simulated. Decide in Phase 14.

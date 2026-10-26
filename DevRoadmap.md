# Development & Deployment Roadmap

A step-by-step path from pre-development to a deployed, quantified RAG demo. This is a working document — update it as reality diverges from the plan (a phase turns out to be harder/easier, an order needs to change). Read alongside [ARCHITECTURE.md](ARCHITECTURE.md) (what we're building and why) and [CLAUDE.md](CLAUDE.md) (working conventions).

**How to read each phase:** Goal → Tasks → Tests to add → CI/CD touchpoint → Advice → Done when. The "CI/CD touchpoint" line is there deliberately — CI/CD isn't one phase, it's a thread that thickens as the project grows. Same for testing: unit tests start on day one, integration tests appear once components connect, "eval tests" (RAGAS/golden dataset) are a third category specific to ML systems.

**Code style: functions vs. classes.** Default to plain functions — something with no state to hold between calls doesn't need a class wrapped around it (the Phase 1 corpus generators are the reference example: `generate_customers(count, seed) -> list[Customer]`, no class needed, nothing persists between calls). Reach for a class specifically where it's earned: real state held across calls (a loaded model, an open client connection) or real polymorphism (multiple interchangeable implementations behind one shared interface). Concretely, three pieces later in this roadmap are deliberately class-based for exactly these reasons, not as a general style choice: `indexing/vectorstore.py` (holds a persistent Chroma client connection, Phase 4), `retrieval/reranker.py` (holds a loaded CrossEncoder model — expensive to reload every call, Phase 6), and `generation/llm.py` (a genuine Strategy pattern: an `LLMProvider` base class with `ClaudeProvider`/`OpenAIProvider` subclasses, directly motivated by the swappable-provider requirement, Phase 8). Everything else — chunking, RRF fusion, the LangGraph node functions in Phase 7 — stays as plain functions, since forcing a class around a stateless transform adds ceremony without adding anything a function doesn't already do.

---

## Concept map — where each idea lives

| Concept | What it means for this project | Where it first appears | Why there, not earlier/later |
|---|---|---|---|
| **Git/GitHub workflow** | Branching, commit hygiene, PRs (even solo) | Phase 0 | Habits are cheap to build before there's much to lose; expensive to retrofit. |
| **Unit testing** | Pure-function tests: chunking logic, RRF math, guardrail regex, corpus generators | Phase 1 onward, one test file per module as it's written | Each pipeline stage is testable in isolation before the next stage exists. |
| **Integration testing** | Multi-component tests: retrieval against a small fixture index, agent routing with mocked LLM calls | Phase 4 (retrieval) onward | Needs ≥2 real components wired together — doesn't exist before indexing works. |
| **Eval testing (RAGAS/LLM-judge)** | Quality-regression tests, threshold-based not exact-match — the ML-specific third leg of the testing pyramid | Phase 9, formalized in Phase 12 | Needs a golden dataset and a full pipeline to run against; this is what makes the project "quantified." |
| **CI (basic)** | Lint/format check on every push | Phase 0 | Nearly free, catches nothing important yet but costs nothing to add. |
| **CI (test-gated)** | Unit + integration suite runs on every PR | Phase 4 onward, matures through the project | Grows with the test suite; no big-bang CI rewrite needed if started early. |
| **CI (eval-gated)** | PR fails if RAGAS/golden-dataset scores regress past a threshold | Phase 12 | The differentiated CI/CD story for a RAG project — needs the eval harness to exist first. |
| **Optimization** | Latency/cost tuning: caching, batching, async I/O, index tuning, prompt trimming | Phase 13, *after* correctness is measured | Optimizing before you can measure correctness risks optimizing the wrong thing, or worse, hiding a bug behind a cache. |
| **Containerization (Docker)** | Packaging the app + Chroma + Langfuse for reproducible local/remote runs | Phase 14 | Only worth doing once there's a full pipeline to package, not per-component. |
| **CD (deployment)** | Getting a running instance reachable outside your machine | Phase 15 | Last, deliberately — a deploy target decided too early constrains earlier choices for no benefit. |
| **Guardrails / red teaming** | Input/output safety checks, adversarial test set | Phases 8, 10 | After generation exists (nothing to guard before there's an output), before the eval harness closes (red team results feed the before/after report). |
| **Time & data freshness** | A fixed `as_of` date for evaluation (frozen corpus); the real date plus index updates for the product (live data) — see ARCHITECTURE.md §4b | Phase 1 (corpus), Phase 7 (agent), Phase 14 (live mode) | Determinism is needed from the very first benchmark; liveness only matters once there's a product to demo. |
| **Observability** | Tracing every pipeline stage via Langfuse | Phase 11 | Wired in once there's a full pipeline worth tracing end-to-end, but *before* the eval harness runs at scale — you want traces while you're generating your first real numbers, not retrofitted after. |

---

## Phase 0 — Environment, Git/GitHub, and hands-on CI

**Goal:** A working dev environment, a Git workflow you'll actually stick to, and enough real, hands-on GitHub Actions experience that the concepts stop being abstract.

**Tasks:**
- `poetry init` + `pyproject.toml`, add `ruff` (lint+format) and `pytest` as dev dependencies.
- Adopt a lightweight branching habit: `main` stays green, work happens on `feature/*` branches, merge via PR even solo — this is what makes CI meaningful (a PR is a natural point to run checks before it hits `main`).
- **Hands-on CI kata** (do this before writing any pipeline code):
  1. Create `.github/workflows/ci.yml` with one job: checkout → setup-python → `poetry install` → `poetry run ruff check .`.
  2. Push it on a branch, open a PR, watch it run in the Actions tab. Read the raw logs, not just the pass/fail icon.
  3. Break it on purpose — introduce a lint error, push, watch it go red, read *why* GitHub shows it failed on that exact line.
  4. Fix it, push again, watch it go green. Now add a second step (`ruff format --check .`) and repeat once.
  5. Add `workflow_dispatch` as a trigger and manually run it from the Actions tab UI, so "trigger" stops being an abstract word.
- Write `.env.example` listing every secret the project will eventually need (`ANTHROPIC_API_KEY`, Langfuse keys) — even before they're used, so the shape of config is visible from day one.

**Tests to add:** None yet — nothing to test. That's fine; CI running with zero tests still validates the *pipeline itself* works.

**CI/CD touchpoint:** This phase *is* the CI/CD touchpoint — basic lint CI goes live here and stays green from the first real commit onward.

**Advice:**
- Don't reach for a pre-written CI template — writing the three-line version yourself first is what makes the concepts stick; copy a fuller template later once you know what each line does.
- Commit the workflow file even while it's trivial. A CI history that starts from commit 3 looks more credible than one bolted on at the end.
- If a step fails for a reason you don't understand, that confusion is the learning moment — read the log fully before asking for help or changing anything.

**Done when:** You can explain, without looking it up, what triggers your workflow, what a runner is, and why the second job step didn't run when the first one failed.

---

## Phase 1 — Synthetic ERP corpus generation

**Goal:** Deterministic, realistic-looking invoices/stock/orders data, generated by Faker, with no real ERP data anywhere.

**Tasks:**
- `src/erp_rag/corpus/schema.py` — define the record shapes (invoice, stock item, order) as dataclasses/Pydantic models.
- `src/erp_rag/corpus/generate_*.py` — one generator per entity type, **seeded** (`Faker.seed(...)`) so runs are reproducible.
- Output to `data/raw/` as CSV or JSON per entity.
- **No hidden clock:** every date-relative value (order dates within "the last 12 months", invoice `overdue` vs. `pending`) is computed against a fixed `CORPUS_REFERENCE_DATE`, passed in as an `as_of` parameter with that default — never `datetime.now()` or Faker's `"today"`. The seed only fixes the random choices; it can't fix the calendar. See ARCHITECTURE.md §4b. *(Added after the first snapshot: the original generators read the real clock, so rebuilding on a different day shifted every order/invoice date and flipped invoice statuses.)*
- Decide corpus size now (rough order of magnitude — hundreds of records, not tens or tens-of-thousands) so later phases aren't blocked on "how much data is there."

**Tests to add (unit):**
- Given a fixed seed, generator output is identical across runs.
- Clock independence: with the system clock mocked to two different days, generator output is still identical. The same-seed test above can't catch a clock dependency on its own, since both of its runs happen on the same day.
- Schema validation: every generated record satisfies its Pydantic model (catches a broken Faker provider immediately).
- Referential sanity: order line items reference stock items that exist, invoices reference orders that exist (structural, not business-logic correctness).

**CI/CD touchpoint:** These are the first real tests in the suite — CI graduates from "lint only" to "lint + pytest."

**Advice:**
- Resist the urge to make the corpus "interesting" with hand-crafted edge cases yet — get the boring, structurally valid version working first. Edge cases (late invoices, out-of-stock items) can be layered in once you know what your golden dataset actually needs to query for (see Phase 3).
- Keep entity relationships (customer → orders → invoices → stock) consistent; a corpus with dangling references will quietly break retrieval later and be confusing to debug.

**Done when:** `poetry run python scripts/build_corpus.py` deterministically produces `data/raw/*.csv` — identical on whatever day it's run — and the unit tests above pass in CI.

---

## Phase 2 — Chunking strategies (implementation)

**Goal:** All three chunking strategies from ARCHITECTURE.md §4 implemented as swappable functions — not yet benchmarked, not yet chosen. (A fourth, semantic/embedding-breakpoint chunking, was considered and deliberately dropped — see ARCHITECTURE.md §4 for the reasoning: it's a poor fit for FK-structured data with no real free-text/topical content.)

**Tasks:**
- `src/erp_rag/ingestion/chunking.py` — one function per strategy, common interface (`list[Record] -> list[Chunk]`), each behind a config flag so `scripts/run_eval.py` can select one later.
- `src/erp_rag/ingestion/loaders.py` — reads `data/raw/`, feeds records into whichever chunking function is active.

**Tests to add (unit):**
- Each chunking strategy, given a small fixed set of input records, produces the expected chunk boundaries and count — this is where bugs in "off by one" chunk splitting get caught before they ever touch a vector store.
- Record-level chunking template renders all expected fields (a silently-dropped field here quietly degrades every downstream retrieval).

**CI/CD touchpoint:** No change — still lint + unit tests, just more of them.

**Advice:**
- Write these as pure functions with no I/O — makes them trivially unit-testable and reusable in the benchmark script later.
- Don't pick a "winner" here even if one looks obviously better by eye — that's exactly the instinct the benchmark step (Phase 4) exists to correct or confirm with numbers.

**Done when:** All three strategies run against the Phase 1 corpus and produce plausible-looking chunks (spot-check a few by hand), with unit tests green.

---

## Phase 3 — Draft golden dataset (seed set)

**Goal:** A small (15–25 example) golden dataset early enough to make every later benchmark actually runnable — expanded to full size in Phase 9.

**Tasks:**
- `eval/golden_dataset/qa_pairs.jsonl` — each entry: question, expected answer (or expected fact), expected source record(s), and a **query-type tag**: `lookup` / `filter` / `aggregation` / `multi-hop`.
- Cover all four query types even in this seed set, in rough proportion to what real usage would look like (per CLAUDE.md: this shapes the agent's tool design later, so don't skip a type because it's harder to write).

**Tests to add:** None (this is data, not code) — but add a schema check: every entry has all required fields, every referenced source record actually exists in the Phase 1 corpus.

**CI/CD touchpoint:** The schema check above runs in CI as a data-validation test — a category distinct from both unit and integration tests, worth naming as such.

**Advice:**
- Write these by hand, not generated by an LLM wholesale — you want them to reflect real ERP-assistant usage, and a hand-written seed set is what you'll trust when a benchmark result looks surprising.
- Multi-hop and aggregation questions are the ones worth the most design attention — they're what justify the agentic layer (Phase 7) existing at all. If every question in this set is answerable by a single lookup, the eval numbers won't be able to show agentic retrieval earning its complexity.

**Done when:** 15–25 entries exist, all four query types represented, schema check green in CI.

---

## Phase 4 — Indexing, hybrid retrieval, and the chunking benchmark

**Goal:** A working Chroma + BM25 hybrid retriever, and the first real benchmark result: which chunking strategy wins.

**Tasks:**
- `src/erp_rag/indexing/vectorstore.py` — Chroma wrapper **as a class** (holds the persistent client connection, see the code-style note above), persist to `data/processed/`; `src/erp_rag/indexing/sparse_index.py` — BM25 via `rank_bm25`.
- `src/erp_rag/retrieval/hybrid_retriever.py` — RRF fusion of dense + sparse results.
- Pick a **scratch embedding model** (e.g. `bge-small-en-v1.5`) purely as a fixed baseline to run the chunking benchmark with — this is not the final embedding choice (that's Phase 5), just a stand-in so chunking can be isolated as the one variable.
- Run all three chunking strategies through the golden dataset (Phase 3), fill in `eval/reports/chunking_benchmark.md` with real numbers, record the decision.

**Tests to add (integration):**
- Build a tiny fixture index (5–10 known records) and assert a known query retrieves the known-correct chunk — this is the first integration test, and it should stay in the suite permanently as a smoke test for "is retrieval fundamentally working."
- RRF fusion: given two known ranked lists, assert the fused ranking matches hand-computed expectations (this one's a unit test on the fusion math specifically, separate from the retrieval integration test).

**CI/CD touchpoint:** CI now has a meaningful integration test, not just units — this is the point where "test suite" starts to mean something beyond lint.

**Advice:**
- Keep the scratch-embedding decision loud and visible (a comment, a config default clearly labeled `# provisional, see Phase 5`) — it's easy to forget this was never meant to be final and accidentally ship it as such.
- A sequential ablation (chunking, then embedding, then reranker, each holding the others fixed) is not the same as a full grid search — cheaper, but it means the chosen chunking strategy is only optimal *given* the scratch embedding, not proven optimal overall. Worth a one-line caveat in the benchmark report itself.
- Use the source record ID(s) as the chunk ID in both indexes. It costs nothing now, and it's what later lets a single new or changed record be updated in place (Phase 14 live mode) instead of rebuilding everything — see ARCHITECTURE.md §4b.

**Done when:** `eval/reports/chunking_benchmark.md` has real numbers and a recorded decision; integration test suite green in CI.

---

## Phase 5 — Embedding model benchmark

**Goal:** Lock the embedding model, using the Phase 4 winning chunking strategy as the new fixed variable.

**Tasks:**
- Re-index the corpus (winning chunking strategy) once per candidate embedding model from ARCHITECTURE.md's shortlist.
- Run each through the golden dataset, fill in `eval/reports/embedding_benchmark.md`.
- Swap the "scratch" embedding config from Phase 4 for the real, benchmarked choice everywhere it's referenced.

**Tests to add:** No new categories — extend the Phase 4 integration test to run against whichever embedding model is currently configured, so it doubles as a regression check when the model changes later.

**CI/CD touchpoint:** None new.

**Advice:** Watch index build time and index size, not just retrieval quality — a marginally-better model that doubles indexing time is a real cost for a project you'll be re-indexing repeatedly during development.

**Done when:** `eval/reports/embedding_benchmark.md` has real numbers and a decision; the "scratch" label is gone from the codebase.

---

## Phase 6 — Cross-encoder reranking benchmark

**Goal:** Decide whether reranking earns its latency, and which reranker, using the now-locked chunking + embedding choices as fixed variables.

**Tasks:**
- `src/erp_rag/retrieval/reranker.py` — **a class** wrapping a `sentence-transformers` `CrossEncoder` (holds the loaded model, see the code-style note above), config-swappable, **including a "none" option** as the baseline.
- Run all candidates (+ no-reranker baseline) through the golden dataset, fill in `eval/reports/reranker_benchmark.md`.

**Tests to add (unit + integration):** Unit test that reranking preserves the candidate set (no chunks silently dropped, only reordered — a common cross-encoder integration bug); integration test extending Phase 4's fixture-index test through the reranking step.

**CI/CD touchpoint:** None new.

**Advice:** Report end-to-end answer quality (faithfulness/relevancy), not just retrieval-metric deltas — a reranker can improve context precision while barely moving the final answer, and that's the number that actually matters for the before/after report.

**Done when:** `eval/reports/reranker_benchmark.md` has real numbers and a decision, including the no-reranker comparison.

---

## Phase 7 — Agentic retrieval layer (LangGraph)

**Goal:** The plan → retrieve → sufficiency-check → re-plan/answer state machine, built to answer the query types drafted in Phase 3 — especially the multi-hop and aggregation ones a single retrieve-then-generate pass can't handle.

**Tasks:**
- `src/erp_rag/agent/graph.py` — the LangGraph state machine; `nodes.py` — individual node logic (planner, retriever call, sufficiency checker); `tools.py` — the tools the planner can invoke (hybrid retrieve, structured metadata filter, aggregate).
- Design the tool set by walking through the Phase 3 golden dataset questions one by one — each query type should map cleanly to a tool or tool combination.
- **Time is an input, not a hidden clock:** the graph's input state carries an explicit `as_of` date, and every time-relative question ("which invoices are overdue?", "orders from last month") is resolved against it. Evaluation passes `CORPUS_REFERENCE_DATE`; the product passes the real current date. Where possible, the filter/aggregation tools derive time-dependent facts (e.g. overdue = unpaid and `due_date < as_of`) instead of trusting a status stored in the chunk text, which goes stale in a live system. See ARCHITECTURE.md §4b.

**Tests to add (integration, with mocked LLM calls):**
- Given a mocked planner response (no real LLM call — deterministic, fast, free), assert the graph routes to the correct tool.
- Given a mocked "insufficient context" signal, assert the graph re-plans rather than answering prematurely — this is the behavior that most easily breaks silently, worth its own explicit test.
- Given the same question ("which invoices are overdue?") and two different `as_of` dates, assert the tools return different invoice sets — proof that time flows in as an input rather than being baked into the code or the index.

**CI/CD touchpoint:** These tests must run without hitting the real Claude API (mocked) so CI stays fast and free — a good moment to introduce the unit/integration-vs-eval distinction concretely: these are integration tests (control flow correctness), not eval tests (answer quality), and they should never need an API key.

**Advice:**
- Build one node at a time and test it in isolation before wiring the full graph — LangGraph state machines are much harder to debug once several nodes are chained and something goes wrong three hops in.
- Log the plan itself (not just the final answer) from day one — Phase 11's Langfuse integration will make this visible properly, but even print-statement visibility now saves real debugging time.

**Done when:** The agent answers every query type in the Phase 3 seed set correctly by manual inspection, and the mocked-LLM integration tests are green in CI.

---

## Phase 8 — Generation and guardrails

**Goal:** Cited answer synthesis, plus the input and output guardrails from ARCHITECTURE.md.

**Tasks:**
- `src/erp_rag/generation/llm.py` — provider abstraction **as a Strategy pattern**: an `LLMProvider` base class, `ClaudeProvider`/`OpenAIProvider` subclasses implementing a shared `generate()` method (Claude default, OpenAI swap-in via config, not hardcoded). Real inheritance and polymorphism here, not ceremony — see the code-style note above.
- `src/erp_rag/guardrails/input_guard.py` — prompt injection + cross-customer data leakage detection.
- `src/erp_rag/guardrails/output_guard.py` — groundedness check against retrieved context, "I don't know" fallback.

**Tests to add (unit + integration):**
- Unit: guardrail regex/classifier logic against known injection strings and known-safe strings (both directions — false positives matter as much as false negatives for a usable assistant).
- Integration: a blocked input never reaches the generator (assert the LLM call is never made — use a mock and assert `call_count == 0`).

**CI/CD touchpoint:** None new, but this is where a `ANTHROPIC_API_KEY` secret first becomes necessary for any CI job that *does* call the real API — keep those jobs separate and clearly marked, since most of the suite should still run without one.

**Advice:** Write the guardrail test cases before the guardrail implementation (a lightweight TDD moment) — for a safety mechanism, knowing exactly what it must catch before writing the regex/classifier avoids designing it around whatever's easiest to implement.

**Done when:** End-to-end pipeline produces cited answers for the golden dataset; guardrail unit + integration tests green.

---

## Phase 9 — Full golden dataset + RAGAS + LLM-as-judge

**Goal:** Expand the Phase 3 seed set to full size, and build the automated eval harness that turns it into numbers.

**Tasks:**
- Expand `qa_pairs.jsonl` to a size that gives statistically meaningful before/after comparisons (aim for 75–150, proportioned across query types).
- `eval/metrics/ragas_eval.py` — faithfulness, answer relevancy, context precision/recall.
- `eval/metrics/llm_judge.py` — a separate Claude prompt with its own rubric (not the generator prompt reused) grading correctness against the actual expected answer.
- `scripts/run_eval.py` — runs the full pipeline against the golden dataset, produces a report. It always passes `as_of=CORPUS_REFERENCE_DATE`, so an eval run next month answers time-relative questions exactly like one today.

**Tests to add:** A "does the eval harness itself work" smoke test — run it against a tiny 2-question subset and assert it produces well-formed output, without needing the full dataset or a large API bill just to verify the harness isn't broken.

**CI/CD touchpoint:** This is the eval harness CI-gating will hook into in Phase 12 — build it standalone first, wire it into CI second, so failures are easy to attribute to one or the other.

**Advice:** Run the eval harness against your own current pipeline *now*, even before every earlier phase's decision feels "final" — an early full-pipeline number, however rough, is what makes every subsequent change legible as an improvement or regression.

**Done when:** `scripts/run_eval.py` produces a full metrics report against the full golden dataset.

---

## Phase 10 — Red teaming

**Goal:** A small adversarial test set proving the guardrails actually hold under realistic attack attempts, not just the happy path.

**Tasks:**
- `eval/redteam/adversarial_prompts.jsonl` — prompt injection attempts, cross-customer data exfiltration attempts, hallucination-bait (out-of-corpus) questions.
- Run these through the pipeline, grade with the LLM-judge from Phase 9 against a "did it leak/comply/hallucinate" rubric.

**Tests to add:** These *are* the tests — treat red-team pass rate as a metric with a floor, same as RAGAS scores.

**CI/CD touchpoint:** Feeds the same eval-gating mechanism as Phase 9's metrics — a red-team regression should block a merge exactly like a RAGAS regression would.

**Advice:** Keep this scoped and realistic — a handful of well-chosen ERP-specific attacks (not a generic jailbreak library dump) says more about your understanding of the actual risk surface than volume would.

**Done when:** Red-team set runs end-to-end and produces a pass/fail rate worth reporting.

---

## Phase 11 — Observability (Langfuse)

**Goal:** Every pipeline stage traced — retrieval, rerank, each agent hop, generation — so debugging and the eval report both have real trace data behind them, not just final-answer inspection.

**Tasks:**
- `docker-compose.yml` entry for self-hosted Langfuse (Postgres + server).
- `src/erp_rag/observability/tracing.py` — instrument each pipeline stage; wire into the LangGraph nodes especially, since that's where "what did the agent actually do" is hardest to see otherwise.
- Re-run the Phase 9 eval harness with tracing on, confirm traces show up correctly correlated to golden dataset runs.

**Tests to add:** A smoke test that tracing calls don't throw when Langfuse is unreachable (observability failing should never take down the actual pipeline) — this is a small but real integration-resilience test worth having.

**CI/CD touchpoint:** None required in CI itself (tracing is a runtime concern, not a test concern) — but do add the Langfuse env vars to `.env.example` and confirm the app degrades gracefully without them, since CI jobs won't have a live Langfuse instance.

**Advice:** Wire this in before running the full-size eval harness in earnest — you want trace data on your *first* full run, not just from whatever run happens to come after you got around to adding observability.

**Done when:** A full eval run produces a complete, inspectable trace tree in the local Langfuse UI.

---

## Phase 12 — CI/CD maturity: eval-gated pipeline

**Goal:** The differentiated CI/CD story — PRs fail if code quality *or* answer quality regresses.

**Tasks:**
- Extend `.github/workflows/ci.yml`: a job running the full unit+integration suite on every push (fast, free, no API key needed); a second job running `scripts/run_eval.py` against a *small* golden-dataset subset on PRs to `main` only (costs money/time — don't run it on every push); a threshold check that fails the job if RAGAS/red-team scores drop below the last-recorded baseline.
- Store the baseline (e.g. a small JSON checked into `eval/reports/` or a CI artifact from the last successful `main` run) so the comparison has something to compare against.

**Tests to add:** None new — this phase is about *gating* on tests/evals that already exist, not writing new ones.

**CI/CD touchpoint:** This phase *is* the CI/CD touchpoint, and the one worth highlighting in a portfolio writeup — most projects gate on tests; gating on retrieval/answer quality is the RAG-specific version of the same idea.

**Advice:**
- Keep the full-size eval run manual (`workflow_dispatch`) or scheduled (nightly `schedule` trigger) rather than on every PR — the small-subset PR gate catches obvious regressions cheaply; the full run is for periodic, deliberate before/after snapshots.
- Make the failure message legible — "context_precision dropped from 0.81 to 0.74 (threshold: 0.78)" is useful; a bare non-zero exit code is not.

**Done when:** A deliberately-introduced regression (e.g. revert to a worse chunking strategy) actually fails the PR check, and you've watched it happen once.

---

## Phase 13 — Optimization pass

**Goal:** Reduce latency/cost *after* correctness is established and measured — never before.

**Tasks:**
- Profile the full pipeline (Langfuse's latency breakdown per stage is the starting point, not a separate profiler).
- Candidate optimizations, applied only where the profile shows a real bottleneck: embedding cache for repeated queries, async I/O for concurrent retrieval + LLM calls, batch indexing during corpus rebuilds, prompt/context trimming to cut generation tokens, Chroma HNSW parameter tuning if the corpus is large enough to matter.
- Re-run the Phase 9 eval harness after each optimization — an optimization that changes answer quality (even accidentally, e.g. an overly aggressive context trim) is a regression, not a win.

**Tests to add:** A latency benchmark, tracked the same way the model benchmarks are (a `eval/reports/optimization_notes.md` following the same before/after template).

**CI/CD touchpoint:** Could feed a latency threshold into Phase 12's gating (optional — only if latency regressions become a real recurring problem worth automating against).

**Advice:** Optimize against Langfuse's actual numbers, not intuition — the stage that "feels slow" during manual testing is often not the one that's actually the bottleneck once measured.

**Done when:** At least one measured, quantified latency/cost improvement exists, with before/after numbers, and eval scores confirmed unchanged.

---

## Phase 14 — Local demo packaging

**Goal:** `docker-compose up` gets a stranger (or a reviewer) from zero to a working chat experience against the full pipeline, locally — served through a real HTTP API, not an in-process script.

**Decided (updated from the original "Streamlit direct-call" default): we're building a public API with FastAPI.** This formalizes the service-layer, UI-agnostic function design already used for indexing/retrieval/generation (see Phase 7-9 discussion) — those functions were written so *any* consumer could call them identically, and the consumer we're committing to is a real HTTP API, not just an in-process Streamlit call.

**Tasks:**
- Build a FastAPI backend (e.g. `src/erp_rag/api/`) exposing the pipeline — a `/query` endpoint (plus a `/health` check) wrapping the agent's single-entry-point function (`answer_query()` or equivalent) discussed during the indexing/retrieval/generation design. FastAPI's automatic OpenAPI/Swagger docs (`/docs`) are a bonus here: a reviewer can exercise the API directly, no UI required, which is its own small portfolio artifact.
- Build a thin UI — Streamlit remains the pragmatic default for the chat interface — that calls the FastAPI backend **over HTTP**, not by importing pipeline functions in-process. This is the one real architecture shift from the original plan: UI and pipeline become two separate processes talking over the API, rather than one monolithic Streamlit script.
- `docker-compose.yml` bringing up: the API container, the UI container, Langfuse (from Phase 11), and Chroma's persistence volume.
- **Live mode (data freshness):** a real ERP assistant works on data that changes every day, so the demo should show the pipeline handling that, not only the frozen eval corpus. `/query` takes an `as_of` date that defaults to the real current date. Add a refresh path (an API endpoint or a `poetry run` script — open decision, see ARCHITECTURE.md §6) that simulates the ERP moving forward (new orders, invoices getting paid or becoming overdue) and updates the indexes: upsert changed/new chunks by record ID in Chroma, rebuild BM25 (`rank_bm25` has no incremental update; cheap at this size). The frozen evaluation corpus stays untouched — live mode works on its own copy.
- A single documented command (`make demo` or a `poetry run` script) — this is the thing a reviewer actually runs, so it needs to work on a clean clone with nothing but Docker and an API key.

**Tests to add:** API-level tests using FastAPI's `TestClient` (hit `/query` with a known question, assert a well-formed response) alongside a container smoke test — the compose stack comes up healthy and both the API and UI respond to a trivial request. For live mode: after a refresh that adds a new record, a query about that record finds it, and the frozen evaluation corpus is unchanged.

**CI/CD touchpoint:** Optional CI job building both Docker images (API + UI) on every push to `main`, catching "works on my machine" packaging drift early.

**Advice:** Test this on a genuinely clean clone (or ask someone else to try it) before considering it done — packaging bugs are invisible from the machine that's had the dependencies installed the whole time.

**Done when:** A clean clone + `docker-compose up` + one documented command produces a working chat UI backed by a real FastAPI service, with `/docs` reachable and independently usable.

---

## Phase 15 — Web deployment

**Goal:** A reachable public (or shareable) URL for the FastAPI backend (and the UI that talks to it).

**This is an open decision, not pre-committed** — revisit when you get here, but the trade-offs as they stand:

| Option | Pros | Cons |
|---|---|---|
| **Hugging Face Spaces** | Free, built for exactly this (AI demo visibility to the audience most likely to evaluate this project), native Docker/Streamlit SDK support | Ephemeral storage complicates persisting Chroma + self-hosted Langfuse; likely means using Langfuse Cloud's free tier for the deployed instance specifically, even if local dev stays self-hosted |
| **Render / Railway** | Real Docker deploy, persistent disks available (small cost), closer to a "production" deployment story | Free tiers are limited/sleep on idle; slightly less AI-portfolio visibility than HF |
| **Fly.io** | Docker-native, generous free allowance, persistent volumes | More infra configuration than the other two; steeper learning curve if this is new |

**Tasks (once a platform is chosen):**
- Wire deployment into CI as an actual CD step: a workflow job that deploys on merge to `main` *after* the Phase 12 test+eval gates pass — this is the point where "CI" and "CD" become genuinely distinct in this project, not just adjacent letters.
- Move secrets from `.env` to the platform's secret store; confirm nothing sensitive is baked into the Docker image itself.

**Tests to add:** A post-deploy smoke test (hit the live URL, assert a 200 and a sane response) — cheap insurance against a deploy that "succeeded" but shipped a broken app.

**CI/CD touchpoint:** This is where the pipeline becomes CI**/CD** in the full sense — gate, then ship, automatically.

**Advice:** Don't let the platform choice block the local demo from being the primary "proof it works" artifact for the portfolio — a live URL can go down, sleep, or run out of free-tier hours; the README and a screen recording of the local demo should never depend on the web deployment staying up.

**Done when:** A public URL serves the same demo as Phase 14, reachable by someone with no local setup.

---

## Phase 16 — Documentation and portfolio polish

**Goal:** Everything the definition-of-done requires is actually visible to a reader who wasn't in these conversations.

**Tasks:**
- README: fill in the Claude Code usage log (per CLAUDE.md's reminder) with what was actually built each session, not just this planning phase.
- Compile the final before/after report from all the `eval/reports/*.md` files into one narrative summary — this is the single artifact most worth linking directly from the README.
- Record a short demo (screen capture of Phase 14's local demo) as a fallback that doesn't depend on Phase 15's deployment staying up.

**Advice:** Write this incrementally as each phase lands, not all at once at the end — a changelog-style Claude Code usage log written contemporaneously is more credible (and easier) than one reconstructed from git log after the fact.

**Done when:** Everything in the original definition of done — functional RAG with an advanced architecture, quantified eval report, observability connected, documented with Claude Code usage traced — is true and linkable from the README.

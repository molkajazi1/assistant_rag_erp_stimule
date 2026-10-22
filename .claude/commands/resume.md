---
description: Generate a full status resume of the project - completed steps, remaining steps, open issues, overall status
---

Command to produce a resume of the current state of the project: all advancement so far, which steps are checked off, which remain, and any open issues - a clear status snapshot of a coding project in progress, not just a context reload.

Usage: `/resume`

## Mission

When `/resume` is run, execute the following sequence in order.

### Step 1 — Load context

Read in full, in this order:

1. `CLAUDE.md` — project conventions, locked decisions, working style.
2. `ARCHITECTURE.md` — what is being built, why, the full decision table.
3. `DevRoadmap.md` — the phased plan, with each phase's tasks and "Done when" criteria.
4. The actual repository state: current branch, `git log --oneline -15`, `git status`, whether the test suite and lint currently pass, and whether the specific files each DevRoadmap phase calls for actually exist on disk (e.g. does `src/erp_rag/ingestion/loaders.py` exist yet). This is the real signal for whether a task is done, not a status note in a doc, which can go stale.

### Step 2 — Produce the status resume

Present a clear progress report, following this structure:

```
Project status resume

**Overall status**
- [one line: which phase is active, how many phases are fully complete]

**Completed**
- [checklist of finished phases/tasks, grouped by phase, each verified against actual repo state - files present, tests passing - not assumed from a doc note alone]

**Remaining**
- [checklist of what is left in the current phase, and the phases still ahead]

**Open issues**
- [anything flagged as pending or unresolved: known gaps, deliberately deferred decisions, TODOs mentioned in docs or code, failing tests if any]

**Current git state**
- [branch, whether it is pushed, whether there are uncommitted changes]
```

### Step 3 — Wait for instructions

Do not start any work on your own initiative after presenting the resume. Wait for the session's actual topic to be given.

## Important rules

- Every "completed" claim must be verified against the actual repository (files exist, tests pass), not copied from a status note in a doc that could be stale.
- If something in a doc contradicts what the repo actually shows, flag it as an open issue rather than silently picking one version as true.
- Do not assume what today's session is about. Wait for instructions rather than guessing a next task and starting on it.
- Communicate in English, no em dashes.

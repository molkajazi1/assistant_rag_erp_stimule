---
description: Save the current workspace state to Git, with a mandatory secret scan before anything is committed
argument-hint: [optional commit message]
---

Command to save the current workspace state to Git, with a systematic check that no secret gets committed.

Usage: `/commit` or `/commit <optional message>`

Argument received (optional user-supplied message): $ARGUMENTS

## Mission

When `/commit` is run, execute the following sequence, in order, and never skip step 3.

### Step 1 — Check the repo state

- Run `git status` to list modified, added, and untracked files.
- If no changes are detected, stop here and report that there's nothing to commit.
- Confirm this is actually an initialized Git repository; if not, say so and go no further.

### Step 2 — Inspect the changes

- Run `git diff` (unstaged changes) and `git diff --cached` (already staged, if any) to see the exact content of every modification.
- For each modified or new file, briefly identify the nature of the change (new file, edit, deletion) and what it corresponds to.
- Flag any file that has no business being in the repo (build artifacts, temp files, exports, personal documents), even if `.gitignore` doesn't cover it yet — report these before continuing.

### Step 3 — Verify no secret is being committed (never skip this step)

- Confirm `.env` and its variants don't show up in `git status` (`.gitignore` should already filter them).
- Inspect the actual diff content (not just file names) for secret-shaped patterns: API keys (`sk-`, `sk-ant-`, `ghp_`, `AKIA...`), values assigned to variables like `*_KEY=`, `*_SECRET=`, `*_TOKEN=`, `*PASSWORD*=` followed by a real value (not just an empty placeholder name), any block that looks like a long base64/hex identifier.
- If a potential secret is detected: stop everything, commit nothing, point to the exact file and line, and wait for instructions.
- Only move to the next step once this check comes back clean.

### Step 4 — Write the commit message

- If a message was supplied as an argument (`$ARGUMENTS`), use it as-is for the main message.
- Otherwise, write a short, clear message from analyzing the diff — what changed and why, not an exhaustive file list.
- The message is in English, one or two lines, no em dashes.

### Step 5 — Commit

- Explicitly add the relevant files with `git add <files>` (never `git add -A` or a blind `git add .`).
- Create the commit with the message written in step 4.
- Run `git status` afterward to confirm the tree is clean.
- Summarize what was committed (files + message).

## Important rules

- Never commit if the secret check (step 3) hasn't been done, or came back with something suspicious.
- Never use `git add -A` or `git add .` — always list files explicitly after inspection.
- Never amend an existing commit (`--amend`) — always create a new one.
- Never use `--no-verify` or bypass a hook.
- Never push automatically — `/commit` only commits locally.
- If suspicious files show up in the diff (unrelated to the requested change, artifacts, personal documents), flag them before committing rather than including them by default.
- Communicate in English, no em dashes.

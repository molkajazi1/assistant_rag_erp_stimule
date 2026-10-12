---
description: Push local commits to the remote, after reviewing exactly what is about to go out
argument-hint: [optional branch name, defaults to the current branch]
---

Command to push committed local changes to the remote (`origin`), with a review of what is being sent and a repeat secret scan before anything leaves the machine.

Usage: `/push` or `/push <branch name>`

Argument received (optional branch name, defaults to the current branch): $ARGUMENTS

Pushing is different from committing: a commit only touches the local repository, but a push changes what everyone else sees on GitHub. Treat every step here as mandatory, in order, and never skip step 3.

## Mission

### Step 1 — Check what there is to push

- Run `git status` and check the current branch (or the branch named in `$ARGUMENTS`, if given).
- Check whether the branch has an upstream set. If it does, compare local commits against it; if not, this will be the first push of this branch.
- If local and remote are already identical, stop here and report that there is nothing to push.
- If the branch has diverged (both local and remote have commits the other doesn't), stop and report this clearly. Do not attempt to resolve it automatically, no merge, no rebase, no pull — that decision belongs to the user.

### Step 2 — Review exactly what is about to be pushed

- List the local commits that are not yet on the remote (`git log @{u}..HEAD` for a tracked branch, or all local commits for a brand new branch).
- For each commit, briefly summarize what it contains, so nothing goes out without a clear picture of what it is.

### Step 3 — Re-scan for secrets before pushing (never skip this step)

- Even though commits should already have passed a secret scan when they were created, re-check the actual diff content of every commit about to be pushed (not just commit messages) for the same secret-shaped patterns: API keys (`sk-`, `sk-ant-`, `ghp_`, `AKIA...`), values assigned to `*_KEY=`, `*_SECRET=`, `*_TOKEN=`, `*PASSWORD*=` followed by a real value, long base64/hex-looking blobs.
- This exists as a second, independent check in case a commit was made outside of `/commit` (a manual `git commit`, another tool, an amend) and never went through that scan.
- If anything suspicious is found: stop completely, push nothing, point to the exact commit, file, and line, and wait for instructions.
- Only move to the next step once this check comes back clean.

### Step 4 — Safety checks on the push itself

- If the target branch is `main` or `master`, stop and ask for explicit confirmation before continuing. Pushing straight to the trunk branch skips the PR/CI review this project is built around, so it needs a deliberate yes, not an assumed one.
- Never use `--force` or `--force-with-lease` unless explicitly, specifically instructed to in that exact moment. A diverged branch is reported in step 1, not force-pushed over.
- If there is no upstream yet, the push will need `-u` to set tracking. If one already exists, a plain push is enough.

### Step 5 — Push and confirm

- Run the push.
- Run `git status` and/or `git log` afterward to confirm local and remote now match.
- If GitHub returns a "create a pull request" link for a newly pushed branch, surface it.
- Summarize what was pushed: branch, commits, and current remote state.

## Important rules

- Never force push under any circumstance without an explicit, specific, in-the-moment instruction to do so.
- Never push directly to `main` or `master` without flagging it and getting explicit confirmation first.
- Never try to resolve a diverged or non-fast-forward state automatically, no auto-merge, no auto-rebase, no auto-pull. Stop and report, let the user decide.
- Never open or merge a pull request as part of this command. Pushing a branch is a separate action from proposing or merging it.
- Always show which commits are about to be pushed before pushing them.
- Always re-run the secret scan on the commits about to be pushed. Do not assume `/commit` already covered it.
- Communicate in English, no em dashes.

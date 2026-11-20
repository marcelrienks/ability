---
name: ability.git.repo-sync
description: "Stage all changes, commit with a generated message, pull with merge-conflict resolution, and push to remote. Asks for confirmation before changing the remote unless `yes` is passed."
io: external
install: global,project
argument-hint: "[yes]"
---

# Git Repo Sync

Complete git synchronization workflow with change summarization and conflict resolution. Operates on the git repository in the current working directory.

## I/O exception

Declared `io: external` (default rule is `data/` in, `<repo root>/<skill-name>/` out).

- Subject: the git repository in the current working directory. No input from `data/`.
- Writes: git history and remote (after confirmation, below). Sync log appended at `<repo root>/ability.git.repo-sync/sync.log` (timestamp, branch, commit hash or `none`, result). Resolve with `python3 .claude/skills/ability.git.common/scripts/ability_paths.py output ability.git.repo-sync`.

## Confirmation (external system)

Pull and push change the remote or local history. Before step 1, show the current branch, remote, and `git status --short`, and ask the user to confirm. Skip the question only when the `yes` arg is passed.

## Workflow

### 1. Stage all changes
Run `git add .`.

### 2. Generate summary and commit
Analyze the staged changes with `git diff --cached --stat` and `git diff --cached`. Generate a concise commit message that summarizes all changes, then run `git commit -m "<message>"`.

The message should:
- Be concise but descriptive
- Start with a capitalized action verb
- Use present tense

Examples: "Add user authentication module", "Fix database connection timeout issue", "Refactor utility functions for better performance".

### 3. Pull from remote with merge
Run `git pull origin <current-branch>`.

### 4. Handle merge conflicts
If the pull conflicts:
- Run `git status` to identify conflicted files
- Review the conflict markers in each file
- Resolve: prefer remote changes (assume authoritative); if both are equally valid, merge manually to preserve both
- `git add <file>` to mark resolved
- Complete the merge with `git commit` (no message needed)

### 5. Push to remote
Run `git push origin <current-branch>`.

### 6. Log
Append the result line to the sync log.

## Important notes

- Requires a git repository in the working directory.
- The user needs push permission on the remote, and the current branch must track a remote branch.
- Stop on the first failed step and report it. Never force-push or bypass a failed step.

## Autonomy boundary

This skill is strictly user-initiated.

- Do NOT run it automatically after edits, code generation, or any other operation.
- Do NOT treat one run as authorization for future git operations.
- Do NOT bundle git operations into other workflows without explicit user consent.
- Within one triggered run, the steps above proceed without further prompts (after confirmation). The next run needs a new explicit request: "run git sync", "sync changes", `/ability.git.repo-sync`, or similar.

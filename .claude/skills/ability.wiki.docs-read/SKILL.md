---
name: ability.wiki.docs-read
description: "Analyze the wiki and persist a context map, preventing redundant reading."
io: external
install: project
argument-hint: "[refresh]"
---

# Wiki Docs Read

Analyzes project documentation and distills it into a persistent context file the agent reuses to maintain state across interactions.

## I/O exception

Declared `io: external` (default rule is `data/` in, `<repo root>/<skill-name>/` out).

- Reads: the project in the current directory: root `README.md` and `.md` files under `wiki/`.
- Writes: `<project>/.cel/context.md` (created automatically). No other files.

## Workflow

### 1. Check for existing context
```bash
python3 .claude/skills/ability.wiki.docs-read/scripts/hashes.py check
```
- `.cel/context.md` missing → go to step 2 (full scan).
- `refresh` arg passed → skip the check, go to step 2 (forced rescan).
- Exit 0 (`MATCH`) → **halt**. Read `context.md` only and give the cache-hit output (step 5).
- Exit 1 (hashes differ) → go to step 2.

### 2. Deep ingestion (recursive search)
Search the root and all subdirectories for:
- **Primary:** `README.md` (and variants like `.txt` or `.markdown`).
- **Secondary:** all `.md` files throughout the tree.
- **Linked assets:** follow links only to diagrams (`.mmd`, `.svg`), images, or referenced `.txt` files.
- **Exclusions** (directory or file name matches):
  - Dot-prefixed directories (`.specify`, `.cel`, `.github`)
  - `specs/`, `node_modules/`
  - Any directory or file whose name contains `archive`, `original`, `orig`, `backup`, or `bak` (case-insensitive, e.g. `docs_backup/`, `README.orig.md`)
  - Addons, plugins, and external libraries (`addons/`, `plugins/`, `vendor/`, `third_party/`, `external/`, `lib/`, `libs/`)
- **Project files only:** do not read documentation bundled with dependencies, packages, or externally sourced libraries.
- Read each file in full, not a snippet.

### 3. Context distillation
Process the findings into:
- **Project Purpose:** the what and why
- **Architecture & Tech Stack:** languages, frameworks, structural patterns
- **Key Workflows:** critical paths from diagrams and docs (interpret Mermaid)
- **Documentation Map:** where specific information lives (e.g. "API specs in /wiki/api")

### 4. Persistence
Write `.cel/context.md` as a "Technical Brief" optimized for LLM consumption, with a timestamp of the last deep read.
- The file name MUST be exactly `context.md` (lowercase).
- Then record hashes of all `.md` files in `wiki/` (excluding `wiki/raw/`) and the root `README.md`:
  ```bash
  python3 .claude/skills/ability.wiki.docs-read/scripts/hashes.py write
  ```
- This file is the agent's state for future requests.

### 5. Output (2-3 sentences)
- **Cache hit**: "Project context loaded from cache (last read: [DATE]). Ready."
- **Cache miss / docs changed**: "Project analyzed. Context persisted with hashes. Ready."
- **Refresh**: "Forced refresh: project re-scanned, context updated. Ready."

## Notes

- Goal: move from "reading" to "knowing". Reuse cached context when hashes match.
- Hash check is automatic: if the wiki changes, a rescan triggers without `refresh`. Use `refresh` after a major wiki restructure.
- Reads wiki only, not source code (unless explicitly linked).

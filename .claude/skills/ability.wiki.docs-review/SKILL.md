---
name: ability.wiki.docs-review
description: "Review the project wiki for fallacies, contradictions, and inconsistencies."
io: external
install: project
argument-hint: "[auto]"
---

# Wiki Docs Review

Three-phase review of the wiki and root README, identifying and resolving fallacies, contradictions, and inconsistencies. Does not analyze `wiki/raw/`.

## I/O exception

Declared `io: external` (default rule is `data/` in, `<repo root>/<skill-name>/` out).

- Reads: the project in the current directory: root `README.md` and `.md` files in `wiki/` (not `wiki/raw/`).
- Writes: fixes applied in place to those same files, after each resolved issue.

## Workflow

**Read every file in full** (wiki and root README).

### Phase 1: Fallacy analysis
Detects:
- Appeal to authority (assuming wiki content is correct without verification)
- Self-contradictions (X and not-X in wiki structure)
- False attribution (files/sections claiming topics they don't cover)
- Vague scope ambiguity (unclear which file documents a topic)
- Unsupported assumptions (facts stated without evidence)
- Incomplete documentation (critical sections missing or inadequate)

### Phase 2: Contradiction analysis
Detects:
- Wiki vs. root README mismatches
- Same topic documented differently in different files
- Conflicting workflow steps
- Conflicting scope or definitions
- Outdated vs. current procedures

### Phase 3: Inconsistency analysis
Detects:
- File organization problems (scattered files, unclear hierarchy)
- Formatting differences (headings, lists, code blocks)
- Terminology differences (same concept, different names)
- Broken or outdated cross-references
- README vs. wiki organization mismatches

### Per-issue process
Phases run in order; fallacy fixes can resolve some contradictions. For each issue:
1. State it with file path, line, and quoted text (both statements for contradictions)
2. Explain why it is a problem and its impact
3. Present resolution options (interactive Q&A standard below)
4. Update the codebase (wiki or README) with the chosen fix
5. Move to the next issue

With `auto`, skip the questions and pick the best option: prefer explicit clarity, reduce ambiguity, make minimal surgical changes, avoid over-engineering.

## Interactive Q&A standard

Use this format for every interactive prompt unless the user asks for another style.

- Present issues one-by-one or grouped, each with 2-3 options. Users reply with compact codes (`1A, 2B, 3C`) or `auto`.
- Per item: **Issue header** (e.g. "Issue 1 — False attribution"), **Location** (file + short quote), **Why** (one line), **Options** (`A`/`B`/`C` with outcome and trade-off), **Selection prompt** (how to reply), **Next step** (what happens after the choice).
- The assistant may propose a default used on `auto` (clarity first, minimal change) and documents it.
- Before edits give a 1-2 sentence preamble. After edits summarize files changed and update the status.
- Preserve content, prefer surgical edits, require explicit approval unless `auto`, and log all changes for review.

## Notes

- Scope: wiki and root README only; `wiki/raw/` excluded.
- Changes apply after each resolution, so later analysis sees earlier fixes.
- Finish with a file-level summary so the user can review all changes before committing.
- Works well after `/ability.wiki.docs-write` or `/ability.wiki.docs-simplify`.

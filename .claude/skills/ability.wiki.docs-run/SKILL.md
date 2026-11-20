---
name: ability.wiki.docs-run
io: external
install: project
description: "Orchestrator: runs the wiki docs pipeline (init, read, write, simplify, optional review) in order, passing shared args down and stopping on first failure."
argument-hint: "[overwrite] [review] [auto]"
---

# Wiki Docs Run

Orchestrator for the wiki docs group. Owns `ability.wiki.docs-init`, `ability.wiki.docs-read`, `ability.wiki.docs-write`, `ability.wiki.docs-simplify`, `ability.wiki.docs-review` and the hidden `ability.wiki.common`.

## I/O exception

Declared `io: external` (default rule is `data/` in, `<repo root>/<skill-name>/` out). Every stage works in place on the project in the current directory: `wiki/`, `wiki/raw/`, `.cel/context.md`, and the root `README.md` (see each stage's own I/O exception).

## Args

| Arg | Passed to | Effect |
|-----|-----------|--------|
| `overwrite` | `docs-write` | Replace all generated docs instead of updating |
| `review` | adds stage 5 | Also run `docs-review` |
| `auto` | `docs-review` | Review picks best options without asking |

`docs-simplify` always runs with `force` inside this orchestrator (no confirmation pause). Run `/ability.wiki.docs-simplify` alone for the interactive plan.

## Stages

Run each by following its skill's SKILL.md in full. After each stage, verify its guard artifact exists before continuing. `docs-init` and `docs-write` also invoke `docs-read` / `docs-simplify` themselves; the repeat run is a cache hit or a no-op.

| # | Skill | Args | Guard artifact |
|---|-------|------|----------------|
| 1 | `ability.wiki.docs-init` | none | `wiki/raw/` exists |
| 2 | `ability.wiki.docs-read` | none | `.cel/context.md` |
| 3 | `ability.wiki.docs-write` | `overwrite` if passed | `wiki/overview.md` |
| 4 | `ability.wiki.docs-simplify` | `force` | `wiki/` still has markdown files |
| 5 | `ability.wiki.docs-review` (only with `review`) | `auto` if passed | stage completes with a change summary |

## Rules

- Run stages strictly in order.
- **Stop on the first failure** (stage error or missing guard artifact). Report which stage failed and why. Never skip, bypass, or fake a failed guard, and do not run later stages.
- Pass only the args above; do not invent new ones.
- Finish with a short summary: stages run and the files changed in `wiki/`.

---
name: ability.wiki.docs-simplify
description: "Audit and simplify the project wiki by consolidating redundancy and eliminating duplicates."
io: external
install: project
argument-hint: "[force]"
---

# Wiki Docs Simplify

Audits all wiki markdown files, identifies inefficiencies and inconsistencies, plans a consolidation, and executes it while preserving all essential information.

**Value-preservation rule:** simplification, consolidation, and reduced verbosity MUST NOT reduce the substantive value or functionality of any document. Reject or rephrase any change that removes essential information, examples, commands, or operational steps.

## I/O exception

Declared `io: external` (default rule is `meta/` in, `<repo root>/<skill-name>/` out).

- Reads: the project in the current directory: all `.md` files in `wiki/` (not `wiki/raw/`), plus `.cel/context.md` and the codebase for context.
- Writes: only markdown files in `<project>/wiki/` (consolidated, renamed, or deleted in place). `wiki/raw/` is never modified.

## Workflow

### Phase 1: Analyze
1. Load project context (`.cel/context.md` if available; scan the codebase as needed for structure, technologies, patterns).
2. Locate all `.md` files in `wiki/` (excluding `wiki/raw/`).
3. **Read each file in full**, extracting names, purposes, headers, content, frontmatter.
4. Identify, within and across files:
   - **Duplication**: identical or near-identical content
   - **Redundancy**: overlapping information that could be consolidated
   - **Inconsistency**: conflicting terminology or formatting
   - **Contradictions**: direct conflicts between statements
   - **Verbosity**: explanations that can be condensed
5. Map relationships and assess the key value of each file.

### Phase 2: Plan
Create the plan with:
1. Content groups to consolidate
2. Duplicates to eliminate
3. Authoritative versions for contradictions
4. Proposed simplified file structure
5. Naming: single-word lowercase (e.g. `setup.md`, `install.md`, `guide.md`, `api.md`, `config.md`, `faq.md`, `troubleshoot.md`)
6. Execution steps (consolidations, deletions, rewrites)
7. Estimated impact (content reduction, quality improvements)

### Phase 3: Confirmation
Show the plan, highlight key decisions, and ask the user to reply "Proceed", "Refine [concern]", or propose changes. Adjust and repeat until approved. **Skipped when `force` is passed.**

### Phase 4: Implement
In `wiki/`:
1. Create consolidated files with unified content
2. Apply single-word lowercase naming
3. Preserve all critical information
4. Delete redundant or superseded files (flag for removal, do not archive)
5. Fix broken cross-references
6. Verify the structure is complete
7. Provide a before/after summary showing the improvements

Standard names: `setup.md`, `install.md`, `guide.md`, `tutorial.md`, `api.md`, `config.md`, `faq.md`, `troubleshoot.md`, `contributing.md`, `license.md`, `changelog.md`. Root `README.md` is not created in the wiki.

## Notes

- Confirmation is mandatory by default. `force` auto-implements the best solutions (used by `/ability.wiki.docs-run`).
- Modification scope: only `wiki/` markdown. Analysis scope: full project context.
- Called with `force` by `/ability.wiki.docs-write`. Next stage: `/ability.wiki.docs-review`.

---
name: ability.wiki.docs-write
description: "Generate and update project documentation by scanning the codebase and existing context."
io: external
install: project
argument-hint: "[overwrite]"
---

# Wiki Docs Write

Generates baseline project documentation by analyzing the codebase: structure, functionality, and intent. Produces minimal but comprehensive docs in the wiki directory covering the known scope of the project, building on existing documentation and context.

## I/O exception

Declared `io: external` (default rule is `data/` in, `<repo root>/<skill-name>/` out).

- Reads: the whole project in the current directory (codebase, README, `wiki/`, `.cel/context.md`).
- Writes: `<project>/wiki/*.md` (creating and updating files in place), plus whatever `docs-init`, `docs-read` and `docs-simplify` write when invoked below.

## Workflow

### 1. Initialize and load context
Create the wiki structure if needed (`/ability.wiki.docs-init`) and load existing project context (`/ability.wiki.docs-read`).

### 2. Codebase analysis
Scan the project to understand:
1. **Project structure**: directory layout, key folders and their purposes, file distribution
2. **Technology & stack**: languages, frameworks, major dependencies, build tools and scripts, package managers, config file types (package.json, pyproject.toml, ...)
3. **Key components**: entry points (main.ts, app.py, index.js, ...), config files and env templates, scripts and automation (Makefile, scripts/), dependencies and versions, API patterns or exposed interfaces
4. **Development patterns**: folder conventions (src/, test/, dist/), module/package structure, testing setup, build process, dev vs. production patterns
5. **Existing documentation**: README purpose and content, existing wiki files and scope, known workflows

### 3. Generate documentation
Generate or update minimal files in `wiki/`: `overview.md`, `structure.md`, `setup.md`, `development.md`, `config.md`, `scripts.md`, and optionally `api.md`, `deployment.md`, `troubleshoot.md` (based on detected project type).

### 4. Manage content and simplify
- Default: update existing files. `overwrite`: replace all generated docs.
- Then invoke `/ability.wiki.docs-simplify force` to consolidate automatically (no manual confirmation).

## Notes

- Works with `docs-init`, `docs-read` and `docs-simplify`.
- Preserves critical information while generating minimal, focused documentation. Uses the codebase as well as existing docs.
- File naming: all wiki files use single-word, lowercase names (e.g. `setup.md`). `README.md` stays at the project root.

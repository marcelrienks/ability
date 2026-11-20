---
name: ability.screen.capture-read
description: "Analyze the latest screenshot (or clipboard image) and answer questions about it in the context of the current session."
io: external
install: global
argument-hint: "[question]"
---

# Screen Capture Read

Finds the most recent screenshot from the system's default screenshot locations, then analyzes it in the context of the current work.

## I/O exception

Declared `io: external` (default rule is `meta/` in, `<repo root>/<skill-name>/` out).

- Reads: OS screenshot locations in `.claude/skills/ability.screen.capture-read/config/screenshot_dirs.json`, or the clipboard.
- Writes: only the staged copy `<repo root>/ability.screen.capture-read/latest.<ext>`. Analysis works on this copy; the original is never modified.
- Read-only against external systems. No network calls.

## Workflow

1. **Find and stage** the latest screenshot:
   ```bash
   python3 .claude/skills/ability.screen.capture-read/scripts/find_screenshot.py
   ```
   The script detects the platform, searches the configured directories for images (PNG, JPEG, GIF) modified within `recency_minutes` (default 2), and falls back to the clipboard if none is found. It prints the staged path. Exit 1 means nothing was found: tell the user and stop.
2. **Load the image** from the printed path with the Read tool.
3. **Analyze** in the context of the current session. Cover what is relevant, such as:
   - Error messages or stack traces
   - State of the code editor or terminal
   - UI elements, logs, or diagnostics tied to the current work
   - Expected vs. actual behavior
   - Recommendations based on what is visible and the session activity
4. If the user passed a `question`, answer that first.

## Platform details

| Platform | Default locations | Clipboard fallback |
|----------|-------------------|--------------------|
| macOS | `~/Documents`, `~/Desktop` | `pngpaste` (user-installed; fallback disabled if absent) |
| Windows | `~/Pictures/Screenshots` | PowerShell clipboard image |
| Linux | `~/Pictures/Screenshots` | `xclip` |
| WSL | `/mnt/c/Users/*/Pictures/Screenshots`, `~/Pictures/Screenshots` | PowerShell clipboard image |

Change locations, formats, or the recency window in the config file.

## Autonomy

Runs only on explicit user invocation. Platform detection and directory/clipboard checks happen inside that run; the skill never starts runs on its own.

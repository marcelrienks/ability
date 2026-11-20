# ability.screen.common

Hidden shared lib for the `screen` domain. Never run directly.

- `scripts/ability_paths.py` resolves paths for the I/O contract (input from `meta/`, output to `<repo root>/<skill-name>/`). Must stay identical across domains (enforced by tests).

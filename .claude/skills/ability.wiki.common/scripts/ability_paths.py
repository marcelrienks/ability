#!/usr/bin/env python3
"""Shared path helper for ability skills. Enforces the I/O contract.

Input:  read only from <root>/meta/. Anything outside is refused.
Output: write only to <root>/<skill-name>/. Created on demand.

<root> is the repo root when running from a clone. For a deployed skill, the deploy
script writes install.json next to scripts/ (in this *.common folder) holding the root:
the project directory (project scope) or ~/.ability (global scope).

CLI (prints an absolute path):
  ability_paths.py root
  ability_paths.py input [REL]       path under meta/ (refuses escapes)
  ability_paths.py output SKILL      output folder of SKILL (created)
  ability_paths.py upstream SKILL    output folder of an earlier stage (read only; exit 1 if absent)
  ability_paths.py config SKILL      SKILL/config inside the skills folder
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL_RE = re.compile(r"^ability(\.[a-z0-9]+){1,2}(-[a-z0-9]+)*$")


def repo_root() -> Path:
    marker = Path(__file__).resolve().parents[1] / "install.json"
    if marker.is_file():
        return Path(json.loads(marker.read_text())["root"])
    for parent in Path(__file__).resolve().parents:
        if (parent / ".claude" / "skills").is_dir():
            return parent
    raise RuntimeError("repo root not found (no .claude/skills above this script)")


def meta_dir() -> Path:
    return repo_root() / "meta"


def input_path(rel: str = ".") -> Path:
    meta = meta_dir().resolve()
    path = (meta / rel).resolve()
    if path != meta and meta not in path.parents:
        raise ValueError(f"input outside meta/ refused: {rel}")
    return path


def _check_skill(skill: str) -> None:
    if not SKILL_RE.match(skill):
        raise ValueError(f"invalid skill name: {skill}")


def output_dir(skill: str) -> Path:
    _check_skill(skill)
    path = repo_root() / skill
    path.mkdir(parents=True, exist_ok=True)
    return path


def upstream_dir(skill: str) -> Path:
    """Earlier stage's folder. Read only, never created here."""
    _check_skill(skill)
    return repo_root() / skill


def config_dir(skill: str) -> Path:
    _check_skill(skill)
    return Path(__file__).resolve().parents[2] / skill / "config"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("root")
    sub.add_parser("input").add_argument("rel", nargs="?", default=".")
    for name in ("output", "upstream", "config"):
        sub.add_parser(name).add_argument("skill")
    args = parser.parse_args()
    try:
        if args.cmd == "root":
            print(repo_root())
        elif args.cmd == "input":
            print(input_path(args.rel))
        elif args.cmd == "output":
            print(output_dir(args.skill))
        elif args.cmd == "upstream":
            path = upstream_dir(args.skill)
            if not path.is_dir():
                print(f"upstream missing: {path}", file=sys.stderr)
                return 1
            print(path)
        else:
            print(config_dir(args.skill))
    except ValueError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

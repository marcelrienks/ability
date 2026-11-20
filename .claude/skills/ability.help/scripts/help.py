#!/usr/bin/env python3
"""Shared help printer for ability skills. Local only, no external calls.

Usage:
  help.py                                  all domains
  help.py --domain D                       one domain
  help.py --domain D --category C          one category (domains that use categories)

Reads name, description and argument-hint from each skills' SKILL.md frontmatter.
Help and *-common skills are not listed.
"""
import argparse
import re
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    fields = {}
    for line in (match.group(1).splitlines() if match else []):
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def summary(description: str) -> str:
    return re.split(r"(?<=[.!?])\s", description.strip(), maxsplit=1)[0]


def collect() -> dict:
    tree: dict = {}
    for folder in sorted(SKILLS.iterdir()):
        skill_md = folder / "SKILL.md"
        parts = folder.name.split(".")
        if not skill_md.is_file() or len(parts) != 3:
            continue
        domain, leaf = parts[1], parts[2]
        category, sep, function = leaf.partition("-")
        if not sep:  # flat domain.function skill: no category level
            category, function = None, leaf
        if function == "help" or function == "common":
            continue
        meta = frontmatter(skill_md)
        tree.setdefault(domain, {}).setdefault(category, []).append(
            (folder.name, meta.get("argument-hint", ""), summary(meta.get("description", "")))
        )
    return tree


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain")
    parser.add_argument("--category")
    args = parser.parse_args()

    tree = collect()
    if args.domain and args.domain not in tree:
        print(f"unknown domain: {args.domain} (known: {', '.join(sorted(tree))})", file=sys.stderr)
        return 1
    if args.category and args.category not in tree[args.domain]:
        known = ", ".join(sorted(c for c in tree[args.domain] if c)) or "none (flat domain)"
        print(f"unknown category: {args.category} (known: {known})", file=sys.stderr)
        return 1

    for domain in sorted(tree):
        if args.domain and domain != args.domain:
            continue
        print(f"{domain}")
        for category in sorted(tree[domain], key=lambda c: (c is not None, c or "")):
            if args.category and category != args.category:
                continue
            indent = "  "
            if category:
                print(f"  {category}")
                indent = "    "
            for name, hint, text in tree[domain][category]:
                print(f"{indent}/{name} {hint}".rstrip())
                print(f"{indent}    {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

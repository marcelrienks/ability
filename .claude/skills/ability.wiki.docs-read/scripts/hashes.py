#!/usr/bin/env python3
"""MD5 change detection for the wiki context cache (.cel/context.md).

Declared I/O exception: operates on the project in the current directory
(or --project DIR), not on data/.

  hashes.py check   exit 0 if .cel/context.md exists and its recorded hashes match; 1 otherwise
  hashes.py write   record current hashes in a '## Hashes' section of .cel/context.md

Hashed: every .md under wiki/ (excluding wiki/raw/) and the root README.md.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

HEADING = "## Hashes"


def current(root: Path) -> dict:
    wiki = root / "wiki"
    files = {f"wiki/{p.relative_to(wiki).as_posix()}": p
             for p in wiki.rglob("*.md") if p.relative_to(wiki).parts[0] != "raw"} if wiki.is_dir() else {}
    if (root / "README.md").is_file():
        files["README.md"] = root / "README.md"
    return {k: hashlib.md5(v.read_bytes()).hexdigest() for k, v in sorted(files.items())}


def recorded(context: Path) -> dict:
    text = context.read_text(encoding="utf-8")
    section = text.split(HEADING, 1)[1] if HEADING in text else ""
    return {m.group(2): m.group(1) for m in re.finditer(r"^- ([0-9a-f]{32})  (.+)$", section, re.M)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["check", "write"])
    parser.add_argument("--project", default=".")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    context = root / ".cel" / "context.md"
    hashes = current(root)

    if args.command == "write":
        if not context.is_file():
            print("write .cel/context.md first", file=sys.stderr)
            return 1
        text = context.read_text(encoding="utf-8").split(HEADING, 1)[0].rstrip()
        lines = [f"- {h}  {p}" for p, h in hashes.items()]
        context.write_text(text + f"\n\n{HEADING}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"recorded {len(hashes)} hashes")
        return 0

    if not context.is_file():
        print("MISS: no context yet")
        return 1
    stored = recorded(context)
    if stored != hashes:
        changed = sorted(k for k in set(stored) | set(hashes) if stored.get(k) != hashes.get(k))
        print("MISS: changed " + ", ".join(changed))
        return 1
    print("MATCH")
    return 0


if __name__ == "__main__":
    sys.exit(main())

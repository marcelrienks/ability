#!/usr/bin/env python3
"""Deploy ability skills to a project or the user's global skills folder, in an AI agent's convention.

Skills run directly from a clone of this repo. Skills meant to run elsewhere declare where
they may be installed in SKILL.md frontmatter (`install: project`, `global`, or `global,project`;
no `install` key means repo-only). This script installs the eligible ones.

  deploy.py --agent claude  --scope project --project ~/work/myapp
  deploy.py --agent copilot --scope global
  deploy.py --agent agents  --scope global --skill ability.screen.read
  deploy.py --agent claude  --scope global --uninstall
  deploy.py --agent claude  --scope project --project ~/work/myapp --uninstall --skill ability.wiki.docs-run

What lands in the target skills folder, per skill:
  - the skill folder (frontmatter converted to the agent's convention)
  - dependencies: ability.help, the domain help + common, the category help (if any), and every
    skill owned by an orchestrator
  - install.json in each *.common folder, telling ability_paths.py where its root is
Uninstall (`--uninstall`) removes every installed ability.* skill from the target, or only the
`--skill` ones plus dependencies nothing else still needs. It refuses to break a remaining skill.
Skill output folders (<root>/<skill-name>/) are kept unless `--purge-output` is given.
Folders that are not ability.* are never touched.

Repo-relative `.claude/skills/` references and `<repo root>` in the docs are rewritten to
the target's real locations.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / ".claude" / "skills"

# Agent conventions: skills folder per scope, and the frontmatter keys the agent understands.
AGENTS = {
    "claude": {"project": ".claude/skills", "global": "~/.claude/skills",
               "keys": ("name", "description", "argument-hint"), "usage_in_description": False},
    "copilot": {"project": ".github/skills", "global": "~/.copilot/skills",
                "keys": ("name", "description"), "usage_in_description": True},
    "agents": {"project": ".agents/skills", "global": "~/.agents/skills",
               "keys": ("name", "description"), "usage_in_description": True},
}
GLOBAL_ROOT = "~/.ability"
VALID_INSTALL = {"project", "global"}


def split(text: str):
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not match:
        return {}, text
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, match.group(2)


def info(name: str) -> dict:
    fields, _ = split((SRC / name / "SKILL.md").read_text(encoding="utf-8")) if (SRC / name / "SKILL.md").is_file() else ({}, "")
    fields["scopes"] = {s.strip() for s in fields.get("install", "").split(",") if s.strip()}
    return fields


def parts(name: str):
    p = name.split(".")
    return (p[1], p[2]) if len(p) == 3 else (None, None)


def is_helper(name: str) -> bool:
    leaf = parts(name)[1] or ""
    return name == "ability.help" or leaf == "help" or leaf == "common" or leaf.endswith(("-help", "-common"))


def dependencies(name: str, names: list) -> set:
    domain, leaf = parts(name)
    out = {name, "ability.help"}
    if domain:
        out |= {f"ability.{domain}.help", f"ability.{domain}.common"}
    if domain and "-" in leaf:  # category form; flat domain.function skills have no category
        category = leaf.split("-")[0]
        out |= {f"ability.{domain}.{category}-help"}
        out |= {n for n in names if n.startswith(f"ability.{domain}.{category}-") and n.endswith("-common")}
        if leaf.endswith("-run"):  # orchestrator owns every working skill in its category
            out |= {n for n in names if parts(n)[0] == domain and parts(n)[1].startswith(f"{category}-")
                    and not is_helper(n) and n != name}
    return {n for n in out if n in names}


def convert_frontmatter(text: str, name: str, agent: dict) -> str:
    fields, body = split(text)
    description = fields.get("description", "")
    hint = fields.get("argument-hint", "")
    if agent["usage_in_description"]:
        description = f"{description} Usage: `/{name}{' ' + hint if hint else ''}`"
    kept = {"name": fields["name"], "description": description}
    if "argument-hint" in agent["keys"] and hint:
        kept["argument-hint"] = hint
    lines = [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in kept.items()]
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def rewrite_paths(text: str, skills_display: str, root_display: str) -> str:
    text = re.sub(r"(?<!~/)\.claude/skills/", skills_display + "/", text)
    return text.replace("<repo root>", root_display)


def uninstall(args, target: Path, root: Path, names: list) -> int:
    installed = sorted(p.name for p in target.glob("ability.*") if p.is_dir()) if target.is_dir() else []
    if args.skill:
        missing = [n for n in args.skill if n not in installed]
        if missing:
            print(f"not installed in {target}: {', '.join(missing)}", file=sys.stderr)
            return 1
        requested = set(args.skill)
        remaining = {n for n in installed if n not in requested and not is_helper(n)}
        for name in sorted(remaining):
            broken = dependencies(name, names) & requested
            if broken:
                print(f"{name} still needs {', '.join(sorted(broken))}: uninstall {name} too", file=sys.stderr)
                return 1
        needed = set().union(*(dependencies(n, names) for n in remaining)) if remaining else set()
        removal = requested | {d for r in requested for d in dependencies(r, names) if d in installed and d not in needed}
    else:
        removal = set(installed)

    removal &= set(installed)
    if not removal:
        print(f"nothing to uninstall in {target}")
        return 0
    print(f"agent={args.agent} scope={args.scope} target={target}")
    for name in sorted(removal):
        print(f"  remove {name}")
        if not args.dry_run:
            shutil.rmtree(target / name)
    if args.purge_output:
        for name in sorted(removal):
            out = root / name
            if out.is_dir():
                print(f"  purge output {out}")
                if not args.dry_run:
                    shutil.rmtree(out)
        if not args.dry_run and args.scope == "global" and root.is_dir() and not any(root.iterdir()):
            root.rmdir()
    print(f"uninstalled {len(removal)} skill folders")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--scope", required=True, choices=sorted(VALID_INSTALL))
    parser.add_argument("--project", help="target project directory (required for --scope project)")
    parser.add_argument("--home", help="home directory for --scope global (default: your home)")
    parser.add_argument("--skill", action="append",
                        help="deploy (or with --uninstall, remove) only this skill (repeatable); default: all")
    parser.add_argument("--clean", action="store_true", help="remove every ability.* skill from the target before deploying")
    parser.add_argument("--uninstall", action="store_true",
                        help="remove installed ability.* skills (all, or the --skill ones plus unneeded dependencies) and stop")
    parser.add_argument("--purge-output", action="store_true",
                        help="with --uninstall: also delete the removed skills' output folders under the install root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    agent = AGENTS[args.agent]

    home = Path(args.home).expanduser().resolve() if args.home else Path.home()
    if args.scope == "project":
        if not args.project:
            parser.error("--scope project requires --project DIR")
        project = Path(args.project).expanduser().resolve()
        if not project.is_dir():
            parser.error(f"project directory not found: {project}")
        target = project / agent["project"]
        root, root_display, skills_display = project, "<project root>", agent["project"]
    else:
        target = home / agent["global"].removeprefix("~/")
        root, root_display, skills_display = home / ".ability", GLOBAL_ROOT, agent["global"]
    if target.resolve() == SRC.resolve():
        parser.error("target is the source skills folder")

    names = sorted(p.name for p in SRC.iterdir() if p.is_dir())
    if args.purge_output and not args.uninstall:
        parser.error("--purge-output requires --uninstall")
    if args.uninstall:
        return uninstall(args, target, root, names)
    if args.clean:
        for old in sorted(target.glob("ability.*")) if target.is_dir() else []:
            print(f"remove {old}")
            if not args.dry_run:
                shutil.rmtree(old)

    eligible = [n for n in names if not is_helper(n) and args.scope in info(n)["scopes"]]
    chosen = args.skill or eligible
    for name in chosen:
        if name not in names:
            parser.error(f"unknown skill: {name}")
        if args.scope not in info(name)["scopes"]:
            parser.error(f"{name} does not declare install: {args.scope} (declared: {info(name).get('install') or 'repo only'})")
    if not chosen:
        print(f"no skills declare install: {args.scope}")
        return 0

    closure = set()
    for name in chosen:
        closure |= dependencies(name, names)
    for name in sorted(closure):
        if not is_helper(name) and args.scope not in info(name)["scopes"]:
            parser.error(f"{name} is required by {', '.join(chosen)} but does not declare install: {args.scope}")

    print(f"agent={args.agent} scope={args.scope} target={target}")
    for name in sorted(closure):
        print(f"  {'(dep) ' if name not in chosen else ''}{name}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(closure):
        dest = target / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(SRC / name, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for md in dest.rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            if md == dest / "SKILL.md":
                text = convert_frontmatter(text, name, agent)
            md.write_text(rewrite_paths(text, skills_display, root_display), encoding="utf-8")
        if name.endswith("common"):
            (dest / "install.json").write_text(
                json.dumps({"scope": args.scope, "agent": args.agent, "root": str(root)}, indent=2) + "\n")
    print(f"deployed {len(closure)} skill folders ({len(chosen)} requested)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

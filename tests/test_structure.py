"""Structure tests: enforce the ability skills naming and layout rules.

Run from repo root:  python3 -m unittest discover -s tests -v
"""
import re
import subprocess
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"

NAME_RE = re.compile(r"^ability\.(help|[a-z0-9]+\.(help|common|[a-z0-9]+(-[a-z0-9]+)+))$")
DOC_REF_RE = re.compile(r"\.claude/skills/[A-Za-z0-9._/-]*")


def frontmatter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
    fields = {}
    for line in (match.group(1).splitlines() if match else []):
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def folders():
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


def parse(name: str):
    """-> (domain, leaf) for ability.<domain>.<leaf>; (None, None) for ability.help."""
    parts = name.split(".")
    return (parts[1], parts[2]) if len(parts) == 3 else (None, None)


def is_common(name):
    leaf = parse(name)[1]
    return leaf == "common" or (leaf or "").endswith("-common")


def is_help(name):
    leaf = parse(name)[1]
    return name == "ability.help" or leaf == "help" or (leaf or "").endswith("-help")


def is_run(name):
    return (parse(name)[1] or "").endswith("-run")


def working(name):
    return not (is_common(name) or is_help(name) or is_run(name)) and name != "ability.help"


def categories():
    cats = defaultdict(list)
    for folder in folders():
        domain, leaf = parse(folder.name)
        if domain and "-" in leaf:
            cats[(domain, leaf.split("-")[0])].append(folder.name)
    return cats


class Naming(unittest.TestCase):
    def test_folder_names_follow_convention(self):
        for folder in folders():
            self.assertRegex(folder.name, NAME_RE, folder.name)

    def test_skill_md_name_matches_folder(self):
        for folder in folders():
            skill_md = folder / "SKILL.md"
            if is_common(folder.name):
                self.assertFalse(skill_md.exists(), f"{folder.name} is hidden and must not have SKILL.md")
                continue
            self.assertTrue(skill_md.is_file(), f"{folder.name} missing SKILL.md")
            meta = frontmatter(skill_md)
            self.assertEqual(meta.get("name"), folder.name)
            self.assertTrue(meta.get("description"), f"{folder.name} missing description")


class Help(unittest.TestCase):
    def test_every_domain_has_help(self):
        domains = {parse(f.name)[0] for f in folders() if parse(f.name)[0]}
        self.assertTrue((SKILLS / "ability.help").is_dir())
        for domain in domains:
            self.assertTrue((SKILLS / f"ability.{domain}.help").is_dir(), f"missing ability.{domain}.help")

    def test_every_category_has_help(self):
        for (domain, category), names in categories().items():
            self.assertIn(f"ability.{domain}.{category}-help", names, f"{domain}/{category} lacks help skill")

    def test_help_skills_use_shared_script(self):
        for folder in folders():
            if is_help(folder.name):
                text = (folder / "SKILL.md").read_text()
                self.assertIn(".claude/skills/ability.help/scripts/help.py", text, folder.name)

    def test_help_lists_every_working_skill(self):
        out = subprocess.run([sys.executable, str(SKILLS / "ability.help/scripts/help.py")],
                             capture_output=True, text=True, check=True).stdout
        for folder in folders():
            if working(folder.name) or is_run(folder.name):
                self.assertIn(f"/{folder.name}", out)


class Orchestrators(unittest.TestCase):
    def test_run_required_at_two_working_skills(self):
        for (domain, category), names in categories().items():
            if sum(working(n) for n in names) >= 2:
                self.assertTrue(any(is_run(n) for n in names), f"{domain}/{category} needs a *-run orchestrator")

    def test_run_description_starts_with_orchestrator(self):
        for folder in folders():
            if is_run(folder.name):
                self.assertTrue(frontmatter(folder / "SKILL.md")["description"].startswith("Orchestrator:"), folder.name)

    def test_run_covers_every_working_skill_in_category(self):
        for (domain, category), names in categories().items():
            runs = [n for n in names if is_run(n)]
            for run in runs:
                text = (SKILLS / run / "SKILL.md").read_text()
                for name in names:
                    if working(name):
                        self.assertIn(name, text, f"{run} does not reference {name}")

    def test_common_not_inside_orchestrator(self):
        for folder in folders():
            if is_common(folder.name):
                self.assertFalse(any(folder.glob("*-run*")), folder.name)


class IoDeclaration(unittest.TestCase):
    def test_io_value_valid_and_declared(self):
        for folder in folders():
            if is_common(folder.name):
                continue
            meta = frontmatter(folder / "SKILL.md")
            io = meta.get("io", "meta")
            self.assertIn(io, ("meta", "external"), folder.name)
            has_section = "## I/O exception" in (folder / "SKILL.md").read_text()
            self.assertEqual(io == "external", has_section, f"{folder.name}: io: external <-> '## I/O exception' section must match")


class InstallDeclaration(unittest.TestCase):
    @staticmethod
    def scopes(name):
        return {s.strip() for s in frontmatter(SKILLS / name / "SKILL.md").get("install", "").split(",") if s.strip()}

    def test_install_values_valid(self):
        for folder in folders():
            if not is_common(folder.name):
                self.assertLessEqual(self.scopes(folder.name), {"project", "global"}, folder.name)

    def test_external_skills_declare_install(self):
        for folder in folders():
            if not is_common(folder.name) and frontmatter(folder / "SKILL.md").get("io") == "external":
                self.assertTrue(self.scopes(folder.name), f"{folder.name}: io: external needs an install declaration")

    def test_orchestrated_skills_allow_orchestrator_scopes(self):
        for (domain, category), names in categories().items():
            for run in (n for n in names if is_run(n)):
                for name in names:
                    if working(name):
                        self.assertLessEqual(self.scopes(run), self.scopes(name), f"{name} must allow {run}'s scopes")


class Docs(unittest.TestCase):
    def test_no_home_dir_skill_references(self):
        for folder in folders():
            for path in folder.rglob("*.md"):
                self.assertNotIn("~/.claude/skills", path.read_text(), str(path))

    def test_wiki_links_resolve(self):
        for path in [ROOT / "README.md"] + sorted((ROOT / "wiki").glob("*.md")):
            for target in re.findall(r"\]\(([^)#]+)\)", path.read_text()):
                if "://" not in target:
                    self.assertTrue((path.parent / target).exists(), f"{path.name} links to missing {target}")

    def test_referenced_skill_paths_exist(self):
        files = [ROOT / "README.md"] + sorted((ROOT / "wiki").glob("*.md")) + [p for f in folders() for p in f.rglob("*.md")]
        for path in files:
            for ref in DOC_REF_RE.findall(path.read_text()):
                ref = ref.rstrip(".,/")
                if ref.count("/") < 2 or "<" in ref:
                    continue
                self.assertTrue((ROOT / ref).exists(), f"{path.relative_to(ROOT)} references missing {ref}")


class Contract(unittest.TestCase):
    def test_ability_paths_identical_across_domains(self):
        copies = {p.read_bytes() for p in SKILLS.glob("ability.*.common/scripts/ability_paths.py")}
        self.assertGreaterEqual(len(copies), 1)
        self.assertEqual(len(copies), 1, "ability_paths.py copies differ between domains")

    def test_gitignore_covers_outputs_inputs_and_credentials(self):
        text = (ROOT / ".gitignore").read_text()
        for pattern in ("/ability.*/", "meta/*", "config.ini", "!*.ini.example"):
            self.assertIn(pattern, text)

    def test_ability_paths_refuses_outside_meta(self):
        sys.path.insert(0, str(SKILLS / "ability.git.common/scripts"))
        import ability_paths
        for bad in ("../README.md", "/etc/passwd"):
            with self.assertRaises(ValueError):
                ability_paths.input_path(bad)
        self.assertEqual(ability_paths.input_path("."), (ROOT / "meta").resolve())


if __name__ == "__main__":
    unittest.main()

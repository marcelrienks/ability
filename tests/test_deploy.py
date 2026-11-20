"""Deploy tests: scripts/deploy.py installs skills per agent convention and scope.

Run from repo root:  python3 -m unittest discover -s tests -v
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts" / "deploy.py"


def deploy(*args):
    return subprocess.run([sys.executable, str(DEPLOY), *args], capture_output=True, text=True)


def frontmatter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
    return {k.strip(): v.strip().strip('"') for k, _, v in (l.partition(":") for l in match.group(1).splitlines())}


class ProjectScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_deploy(self, agent, folder):
        result = deploy("--agent", agent, "--scope", "project", "--project", str(self.project))
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.project / folder

    def test_claude_layout_and_frontmatter(self):
        skills = self.run_deploy("claude", ".claude/skills")
        for name in ("ability.wiki.docs-run", "ability.wiki.docs-init", "ability.wiki.common",
                     "ability.wiki.docs-help", "ability.wiki.help", "ability.help", "ability.git.sync"):
            self.assertTrue((skills / name).is_dir(), name)
        self.assertFalse((skills / "ability.screen.read").exists(), "global-only skill deployed to project")
        meta = frontmatter(skills / "ability.wiki.docs-read" / "SKILL.md")
        self.assertEqual(set(meta), {"name", "description", "argument-hint"})

    def test_copilot_layout_and_usage_in_description(self):
        skills = self.run_deploy("copilot", ".github/skills")
        meta = frontmatter(skills / "ability.wiki.docs-read" / "SKILL.md")
        self.assertEqual(set(meta), {"name", "description"})
        self.assertIn("Usage: `/ability.wiki.docs-read [refresh]`", meta["description"])

    def test_agents_layout(self):
        skills = self.run_deploy("agents", ".agents/skills")
        self.assertTrue((skills / "ability.wiki.docs-run" / "SKILL.md").is_file())

    def test_paths_rewritten_for_target(self):
        skills = self.run_deploy("copilot", ".github/skills")
        text = (skills / "ability.wiki.docs-read" / "SKILL.md").read_text()
        self.assertIn(".github/skills/ability.wiki.docs-read/scripts/hashes.py", text)
        self.assertNotIn(".claude/skills", text)
        self.assertNotIn("<repo root>", text)

    def test_install_json_root_is_project(self):
        skills = self.run_deploy("claude", ".claude/skills")
        marker = json.loads((skills / "ability.wiki.common" / "install.json").read_text())
        self.assertEqual(marker["scope"], "project")
        self.assertEqual(Path(marker["root"]).resolve(), self.project.resolve())

    def test_deployed_scripts_resolve_project_root(self):
        skills = self.run_deploy("claude", ".claude/skills")
        out = subprocess.run([sys.executable, str(skills / "ability.wiki.common/scripts/ability_paths.py"), "root"],
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(Path(out).resolve(), self.project.resolve())

    def test_deployed_help_lists_only_deployed(self):
        skills = self.run_deploy("claude", ".claude/skills")
        out = subprocess.run([sys.executable, str(skills / "ability.help/scripts/help.py")],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("ability.wiki.docs-init", out)
        self.assertNotIn("ability.screen.read", out)

    def test_redeploy_replaces_and_uninstall_removes(self):
        skills = self.run_deploy("claude", ".claude/skills")
        (skills / "ability.wiki.docs-init" / "stale.txt").write_text("x")
        self.run_deploy("claude", ".claude/skills")
        self.assertFalse((skills / "ability.wiki.docs-init" / "stale.txt").exists())
        (skills / "keep-me").mkdir()
        result = deploy("--agent", "claude", "--scope", "project", "--project", str(self.project), "--uninstall")
        self.assertEqual(result.returncode, 0)
        self.assertEqual([p.name for p in skills.iterdir()], ["keep-me"])


class GlobalScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_global_claude(self):
        result = deploy("--agent", "claude", "--scope", "global", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stderr)
        skills = self.home / ".claude" / "skills"
        self.assertTrue((skills / "ability.screen.read").is_dir())
        self.assertFalse((skills / "ability.wiki.docs-init").exists(), "project-only skill deployed globally")
        text = (skills / "ability.screen.read" / "SKILL.md").read_text()
        self.assertIn("~/.claude/skills/ability.screen.read/scripts/find_screenshot.py", text)
        self.assertIn("~/.ability/", text)
        marker = json.loads((skills / "ability.screen.common" / "install.json").read_text())
        self.assertEqual(Path(marker["root"]).resolve(), (self.home / ".ability").resolve())

    def test_global_copilot_folder(self):
        result = deploy("--agent", "copilot", "--scope", "global", "--home", str(self.home))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / ".copilot" / "skills" / "ability.git.sync").is_dir())

    def test_refuses_undeclared_scope(self):
        result = deploy("--agent", "claude", "--scope", "global", "--home", str(self.home),
                        "--skill", "ability.wiki.docs-init")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not declare install: global", result.stderr)
        self.assertFalse((self.home / ".claude").exists())

    def test_project_scope_requires_project(self):
        result = deploy("--agent", "claude", "--scope", "project")
        self.assertNotEqual(result.returncode, 0)

    def test_dry_run_writes_nothing(self):
        result = deploy("--agent", "claude", "--scope", "global", "--home", str(self.home), "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.home / ".claude").exists())


if __name__ == "__main__":
    unittest.main()

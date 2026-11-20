#!/usr/bin/env python3
"""Find the latest screenshot (or clipboard image) and stage it in this skill's output folder.

Prints the staged file path. Exit 1 if nothing recent was found.
Screenshot locations come from ../config/screenshot_dirs.json (skill settings).
This skill is a declared ingest point: it reads the OS screenshot locations, then
works only on the staged copy.
"""
import glob
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL = "ability.screen.capture-read"
SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "ability.screen.common" / "scripts"))
import ability_paths  # noqa: E402


def detect_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    try:
        if "microsoft" in Path("/proc/version").read_text().lower():
            return "wsl"
    except OSError:
        pass
    return "linux"


def latest_file(plat: str, config: dict):
    cutoff = time.time() - config["recency_minutes"] * 60
    exts = tuple(config["extensions"])
    found = []
    for pattern in config["dirs"][plat]:
        for folder in glob.glob(str(Path(pattern).expanduser())):
            for entry in Path(folder).iterdir():
                if entry.suffix.lower() in exts and entry.is_file() and entry.stat().st_mtime >= cutoff:
                    found.append(entry)
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def clipboard_image(plat: str, dest: Path):
    """Save clipboard image to dest. Returns True on success."""
    if plat == "macos":
        cmd = ["pngpaste", str(dest)]  # requires: brew install pngpaste
    elif plat == "linux":
        cmd = ["sh", "-c", f"xclip -selection clipboard -t image/png -o > '{dest}'"]
    else:  # wsl / windows
        if plat == "wsl":
            winpath = subprocess.run(["wslpath", "-w", str(dest)], capture_output=True, text=True).stdout.strip()
        else:
            winpath = str(dest)
        ps = ("Add-Type -AssemblyName System.Windows.Forms; "
              "$i=[Windows.Forms.Clipboard]::GetImage(); if(-not $i){exit 1}; "
              f"$i.Save('{winpath}')")
        cmd = ["powershell.exe", "-NoProfile", "-Command", ps]
    if shutil.which(cmd[0]) is None:
        print(f"clipboard fallback unavailable: {cmd[0]} not installed", file=sys.stderr)
        return False
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def main() -> int:
    plat = detect_platform()
    config = json.loads((ability_paths.config_dir(SKILL) / "screenshot_dirs.json").read_text())
    out = ability_paths.output_dir(SKILL)

    source = latest_file(plat, config)
    if source:
        dest = out / f"latest{source.suffix.lower()}"
        shutil.copy2(source, dest)
        print(dest)
        return 0

    dest = out / "latest.png"
    if clipboard_image(plat, dest):
        print(dest)
        return 0
    print(f"no screenshot newer than {config['recency_minutes']} min and no clipboard image ({plat})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

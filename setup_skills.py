#!/usr/bin/env python3
"""
setup_skills.py — Install bot-trade skills to AI agent directories

Supports:
  - Claude Code (.claude/skills/)
  - Minara CLI (~/.minara/skills/)
  - Cursor (.cursorrules + .cursor/skills/)
  - Generic (copy to target dir)

Usage:
  python setup_skills.py --target claude
  python setup_skills.py --target minara
  python setup_skills.py --target cursor
  python setup_skills.py --target all
"""
import argparse
import shutil
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"
HOME = Path.home()

TARGETS = {
    "claude": Path(".claude") / "skills",           # Claude Code (project-level)
    "minara": HOME / ".minara" / "skills",           # Minara CLI (global)
    "cursor": Path(".cursor") / "skills",            # Cursor (project-level)
}

SKILL_FILES = [
    "SKILL.md",
    "nado-trading.md",
    "decibel-trading.md",
    "rise-trading.md",
    "delta-neutral.md",
]


def install_skills(target_dir: Path, dry_run: bool = False):
    """Copy all skill files to target directory."""
    print(f"\n[+] Installing skills to: {target_dir}")

    if not SKILLS_DIR.exists():
        print(f"[!] Skills directory not found: {SKILLS_DIR}")
        return False

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_file in SKILL_FILES:
        src = SKILLS_DIR / skill_file
        dst = target_dir / skill_file

        if not src.exists():
            print(f"    [SKIP] {skill_file} (not found)")
            continue

        if dry_run:
            print(f"    [DRY] Would copy: {src} -> {dst}")
        else:
            shutil.copy2(src, dst)
            print(f"    [OK]  {skill_file}")
            installed.append(skill_file)

    return len(installed) > 0


def install_cursor_rules():
    """Create/update .cursorrules with bot-trade context."""
    rules_path = Path(".cursorrules")
    content = """# Bot Trade — DEX Trading Bot
# Nado x Rise x Decibel Multi-Exchange Trading Bot

## Context
This project is a Python-based CLI trading bot for DEX perpetual markets.
Working directory: d:\\bot\\bot trade

## Key Commands
- `python -m bot_trade funding` — scan funding rates
- `python -m bot_trade delta-neutral` — run delta neutral strategy
- `python -m bot_trade volume` — generate trading volume
- `python -m bot_trade indicator` — indicator-based trading
- `python -m bot_trade status` — account status

## Project Structure
- bot_trade/exchanges/ — Exchange adapters (nado, decibel, rise)
- bot_trade/strategies/ — Trading strategies
- bot_trade/cli.py — CLI entry point
- skills/ — AI agent skill files

## Important Notes
- Credentials in .env (never commit)
- Nado: uses nado-cli + nado-protocol SDK
- Decibel: REST read + Aptos on-chain write
- Rise: REST API (requires API key from developer.rise.trade)
"""
    rules_path.write_text(content, encoding="utf-8")
    print(f"    [OK]  .cursorrules created")


def main():
    parser = argparse.ArgumentParser(description="Install bot-trade skills to AI agent")
    parser.add_argument(
        "--target",
        choices=["claude", "minara", "cursor", "all"],
        default="claude",
        help="Target AI agent to install skills for"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it"
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  Bot Trade — Skill Installer")
    print("  Nado x Rise x Decibel")
    print("=" * 55)

    targets_to_install = (
        list(TARGETS.keys()) if args.target == "all" else [args.target]
    )

    success = 0
    for target in targets_to_install:
        target_dir = TARGETS[target]
        ok = install_skills(target_dir, dry_run=args.dry_run)
        if ok:
            success += 1

        if target == "cursor" and not args.dry_run:
            install_cursor_rules()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done! {success}/{len(targets_to_install)} targets installed.")

    if not args.dry_run:
        print("\nNext steps:")
        if "claude" in targets_to_install:
            print("  Claude Code: Skills auto-loaded from .claude/skills/")
            print("  Say: 'scan funding rates di nado dan decibel'")
        if "minara" in targets_to_install:
            print("  Minara: Run `minara chat` and describe your trading goal")
        if "cursor" in targets_to_install:
            print("  Cursor: .cursorrules + .cursor/skills/ updated")


if __name__ == "__main__":
    main()

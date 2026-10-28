# Getting started

You need: Python 3.9+, `pip install -r requirements.txt` (pyyaml; openpyxl for the Revolut parser), `pdftotext` (poppler-utils) for PDF statements (and `playwright` + `playwright install chromium` for the optional dashboard render check), and one AI agent - Claude Code (best supported), or Codex / ChatGPT agents via `AGENTS.md`.

```
git clone <this repo> investassist && cd investassist
python3 scripts/init_workspace.py --demo     # optional: synthetic data, builds a demo dashboard
open data/reports/<today>/dashboard.html
```

## With your own data
1. Remove the demo if you loaded it (delete `data/`, `config/*.yaml`, `CLAUDE.local.md`, `history/*`, `knowledge/*`, `memory/*` except the READMEs), then `python3 scripts/init_workspace.py`.
2. Put every export, statement, CSV and screenshot you have into `data/inbox/`. Anything without an export you will type in later.
3. Start your agent in this folder and say: **"set up"** (Claude Code: just `claude`; it reads `CLAUDE.md`). Other agents: paste `prompts/setup.md`.
4. The `setup` skill asks a few questions (owner, base currency, country, language), writes a parser for each platform from your own files, reconciles totals, looks up FX and instrument data, connects mail if you have a read-only mail connector, runs the first scan, and schedules daily and weekly runs.

## What you get
- `data/reports/<date>/dashboard.html` - what the news touches in your portfolio, top-holding outlook (rise / fall / neutral lean for 4 weeks, sourced), catalysts, mail events, data freshness.
- `data/reports/<date>/daily_digest.md`, weekly `portfolio_report.md`, alerts in `reports/alerts/` and any channel you configure.

## Privacy
Nothing leaves your machine except what your AI agent and web searches send. Everything personal is git-ignored (`data/`, `reports/`, `local/`, `config/*.yaml`, `CLAUDE.local.md`). Check with `git status` before committing anything.

Not financial advice. Leans are tilts from dated sources, action candidates are options for your own review.

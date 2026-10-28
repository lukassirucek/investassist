# Investassist

An AI-agent toolkit that watches your investment portfolio. Give it your own exports, statements and (read-only) e-mail; it builds one portfolio view and, every day and week, scans news, geopolitics, commodities, hazards, housing and platform events against **what you actually own**, then produces:

- a **dashboard** of the positions that news touches, with scenario ranges and action candidates for your review,
- a sourced **rise / fall / neutral lean for your largest holdings** over the next four weeks (with a track record),
- a daily digest, a weekly report and alerts (file, email draft, Slack, push).

It is not financial advice and never places trades. Leans are tilts from dated, linked sources.

## Try it in two minutes
```
pip install pyyaml
python3 scripts/init_workspace.py --demo      # synthetic portfolio, builds data/reports/<today>/dashboard.html
```

## Use it on your data
1. Put your exports/screenshots into `data/inbox/` (after `python3 scripts/init_workspace.py`).
2. Open the folder in **Claude Code** (or Codex / another agent via `AGENTS.md`) and say **"set up"**. The `setup` skill writes a parser for each of your platforms from your own files, reconciles the totals, connects mail if you have a connector, runs the first scan and schedules the daily and weekly runs.

Ready-made parsers for Revolut, Portu, Indigo/Patria, Raiffeisenbank, Investown and Golden Gate, plus typed templates for Zonky, ČSOB Investice, Air Bank and others: [parsers/README.md](parsers/README.md). Details: [docs/getting-started.md](docs/getting-started.md), [docs/index-spec.md](docs/index-spec.md), [docs/scheduling.md](docs/scheduling.md), [docs/architecture.md](docs/architecture.md).

## Privacy
All personal data is git-ignored (`data/`, `reports/`, `local/`, `config/*.yaml`, `CLAUDE.local.md`, `history/`, `knowledge/`, `memory/`). Only code, skills and docs are tracked. Your agent and web searches see what they need to do the work; nothing else is uploaded by this repository.

## Working memory (local only)
`RULES.md` adds: prompt history (`history/`, via hook), researched knowledge (`knowledge/`, `KNOWLEDGE.md`), memory and handovers (`memory/`), and a scripts registry (`SCRIPTS.md`). The first three are git-ignored and created by `scripts/init_workspace.py`; `scripts/check-rules.sh` verifies the setup.

## Layout
`scripts/` deterministic Python - `parsers/` ready-made platform parsers - `.claude/skills/`, `.claude/agents/` agent knowledge - `prompts/` scheduled-run prompts - `templates/` parser template - `examples/` demo data - `docs/`.

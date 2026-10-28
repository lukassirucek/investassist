# Investassist - instructions for Codex, ChatGPT agents and other AI coding agents

This repository is an investment-portfolio assistant. The full rules are in `CLAUDE.md` and apply to every agent: read it first. Tool names differ between agents; the behaviour does not.

## Mapping
- **Skills** live in `.claude/skills/<name>/SKILL.md`. They are plain Markdown procedures: when a task matches a skill's `description`, open that file and follow it step by step. Start with `setup`.
- **Scripts** are normal Python 3 (`pip install pyyaml`; `playwright` only for the dashboard render check): `python3 -I scripts/<name>.py`.
- **Asking the user:** where a skill says AskUserQuestion, ask in chat with concrete options and wait. In an unattended run, choose the most reasonable reading, say which, and continue.
- **Web:** where a skill says WebSearch / WebFetch, use your browsing tool. Open the article and read its date before using it as a source.
- **Mail:** use whatever read-only mail connector you have. If none, ask the user to paste the relevant mails or skip `ingest-email`.
- **Scheduling:** see `docs/scheduling.md` (cron + `codex exec` / `claude -p` with `prompts/daily.md` and `prompts/weekly.md`).
- **Dashboard:** `python3 -I scripts/build_dashboard_html.py` writes `data/reports/<date>/dashboard.html`; open it in a browser. (Claude's Artifact publishing is optional.)

## Start
`python3 scripts/init_workspace.py --demo` to see it work on synthetic data, or follow `prompts/setup.md` for your own data. Personal files are git-ignored: never commit `data/`, `reports/`, `local/`, `config/*.yaml`, `CLAUDE.local.md`.

Put personal rules for your own session in `AGENTS.local.md` (git-ignored).

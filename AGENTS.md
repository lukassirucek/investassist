# Investassist - instructions for Codex, ChatGPT agents and other AI coding agents

This repository is an investment-portfolio assistant. The full rules are in `CLAUDE.md` and `RULES.md` and apply to every agent: read both first (Claude Code imports `RULES.md` automatically; you must open it), then `memory/HANDOVER.md` and `memory/*/MEMORY.md` if they exist. Tool names differ between agents; the behaviour does not.

## Mapping
- **Skills** live in `.claude/skills/<name>/SKILL.md`. They are plain Markdown procedures: when a task matches a skill's `description`, open that file and follow it step by step. Start with `setup`.
- **Scripts** are normal Python 3 (`pip install pyyaml`; `playwright` only for the dashboard render check): `python3 -I scripts/<name>.py`.
- **Asking the user:** where a skill says AskUserQuestion, ask in chat with concrete options and wait. In an unattended run, choose the most reasonable reading, say which, and continue.
- **Web:** where a skill says WebSearch / WebFetch, use your browsing tool. Open the article and read its date before using it as a source.
- **Mail:** use whatever read-only mail connector you have. If none, ask the user to paste the relevant mails or skip `ingest-email`.
- **Scheduling:** see `docs/scheduling.md` (cron + `codex exec` / `claude -p` with `prompts/daily.md` and `prompts/weekly.md`).
- **Dashboard:** `python3 -I scripts/build_dashboard_html.py` writes `data/reports/<date>/dashboard.html`; open it in a browser. (Claude's Artifact publishing is optional.)

## Process mechanisms (RULES.md)
- **Prompt history:** you have no hooks. Log each user prompt: `python3 scripts/prompt-log.py add --who user --prompt - --model "<your model id>"` (prompt on stdin), and at the end of the turn `python3 scripts/prompt-log.py summarize --who user --summary "<max 2 lines>" --model "<your model id>"`.
- **Scripts:** read `SCRIPTS.md` before writing any script; register new ones.
- **Knowledge:** `python3 scripts/knowledge-find.py <terms>` before researching a reference fact; persist with `scripts/knowledge-add.py`.
- **Memory:** write to `memory/codex/` (index `MEMORY.md`); hand over with `scripts/memory-handover.py write --from codex --to claude ...`.
- `history/`, `knowledge/`, `memory/`, `KNOWLEDGE.md` are local and git-ignored. Check: `scripts/check-rules.sh`.

## Start
`python3 scripts/init_workspace.py --demo` to see it work on synthetic data, or follow `prompts/setup.md` for your own data. Personal files are git-ignored: never commit `data/`, `reports/`, `local/`, `config/*.yaml`, `CLAUDE.local.md`, `history/`, `knowledge/`, `memory/`.

Put personal rules for your own session in `AGENTS.local.md` (git-ignored).

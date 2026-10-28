# history

Local prompt history (git-ignored; only this README is tracked). One file per actor per week: `prompts-user-YYYYMMWW.md`, `prompts-<agent>-YYYYMMWW.md`. Rules: `RULES.md` section C. Written by the `UserPromptSubmit` hook in `.claude/settings.json`; for other agents run `scripts/prompt-log.py add`. Every entry carries a `**Model:**` line. Read: `python3 scripts/prompt-log.py show --since 2026-10-01`, whole entry with `--full`.

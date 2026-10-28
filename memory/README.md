# memory

Local agent memory and handovers (git-ignored; only this README is tracked). Rules: `RULES.md` section E. Created by `python3 scripts/init_workspace.py`.

```
memory/
  HANDOVER.md      latest handover (session to session, or Claude <-> Codex/ChatGPT agent)
  handovers/       archive of past handovers: <id>.md
  claude/          Claude Code auto memory (autoMemoryDirectory): MEMORY.md index + topic files
  codex/           memory written by a Codex/ChatGPT agent, same format
  shared/          facts every agent needs: MEMORY.md index + topic files
```

Format (all folders): `MEMORY.md` = index, one line per memory, at most 200 lines: `- [Title](file.md) - one-line hook`. Topic file frontmatter: `name`, `description`, `type` (user | feedback | project | reference), `source` (claude | codex | user), `updated` (YYYY-MM-DD). Body: the fact, why it matters, how to apply. No credentials, no full account numbers.

Memory vs `CLAUDE.local.md`: `CLAUDE.local.md` holds standing rules the owner set (always loaded); memory holds what the agents learned (feedback, platform quirks, decisions, open items).

Handover: sender `python3 scripts/memory-handover.py write --from claude --to codex --summary "..." --next "..."`; receiver reads `HANDOVER.md`, acts, then `... ack --by codex`. The SessionStart hook reports a pending handover.

Audit: `python3 scripts/memory-audit.py` finds Claude memory stored outside the project; `--import` copies it in.

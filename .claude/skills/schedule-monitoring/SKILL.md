---
name: schedule-monitoring
description: Set up the daily and weekly monitoring runs on the user's schedule - Claude Code scheduled tasks if available, otherwise cron or another scheduler running the agent headless with prompts/daily.md and prompts/weekly.md.
---
Ask once (AskUserQuestion): daily time and weekdays (default every day, early morning in the user's timezone from `config/profile.yaml`), weekly day and time (default Monday, right after the daily run), where results go (dashboard path or artifact + alert channels already in `config/alerts.yaml`).

Choose the mechanism by what exists:
1. **Claude Code with a scheduling tool** (scheduled tasks / triggers): create two tasks. Prompt = the contents of `prompts/daily.md` and `prompts/weekly.md`, prefixed with the absolute project path so the run starts in the right folder. Runs need the project files: if the task runs in the cloud and the data is only on this computer, the task must run on this computer (tell the user it only fires while the computer and app are on). State the permission mode the task received. A schedule never trades or sends mail by itself.
2. **Claude Code CLI (cron / launchd / Task Scheduler):** `cd <project> && claude -p "$(cat prompts/daily.md)" --permission-mode acceptEdits --allowedTools "Read,Write,Edit,Bash,WebSearch,WebFetch" >> data/reports/cron.log 2>&1`. Give the exact crontab line for the user's timezone; do not edit the crontab without asking.
3. **Codex / ChatGPT agents:** `cd <project> && codex exec "$(cat prompts/daily.md)"` from cron. Without a scheduler, the user runs the prompt manually; say how.
4. **No agent at all:** the deterministic part still works from cron: `python3 scripts/pipeline.py` (rebuilds indexes, exposure, digest, dashboard from the files). News and mail need the agent.
Dry-run the daily prompt once right now and show the result before declaring it scheduled. Write the schedule, the mechanism and the next run time into `CLAUDE.local.md`. Details: `docs/scheduling.md`.

# Scheduling

The deterministic part (`python3 scripts/pipeline.py`) needs no AI. The monitoring (mail, news, outlook, alerts) is done by an agent running `prompts/daily.md` and `prompts/weekly.md`. The `schedule-monitoring` skill sets this up; these are the options.

| Agent | How |
|---|---|
| Claude Code, scheduling tool available | create scheduled tasks with the prompt files (the skill does it); a task that needs your local files must run on your computer |
| Claude Code CLI | cron / launchd / Task Scheduler: `cd /path/to/investassist && claude -p "$(cat prompts/daily.md)" --permission-mode acceptEdits --allowedTools "Read,Write,Edit,Bash,WebSearch,WebFetch"` |
| Codex | `cd /path/to/investassist && codex exec "$(cat prompts/daily.md)"` |
| Anything else | run the prompt by hand each morning; `pipeline.py` from cron still refreshes numbers |

Example crontab (07:30 daily, Monday weekly at 07:45, local time): 
```
30 7 * * *   cd /path/to/investassist && claude -p "$(cat prompts/daily.md)"  >> data/reports/cron.log 2>&1
45 7 * * 1   cd /path/to/investassist && claude -p "$(cat prompts/weekly.md)" >> data/reports/cron.log 2>&1
```
Scheduled runs are unattended: they never ask questions, trade or send mail unless `config/alerts.yaml` says `email.mode: send`. Mail reading needs a read-only mail connector configured for that agent.

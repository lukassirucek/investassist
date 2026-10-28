---
name: alert-triage
description: Score, dedupe and route findings to channels (push, Slack, Gmail, file) according to config/alerts.yaml.
---
Score = exposure_pct × impact × confidence × urgency; apply `critical_if_any`/`high_if_any`. Dedupe against `reports/alerts/` last 48h. Format alert ≤ 5 lines: `[SEVERITY] <what> | <positions + weight%> | <why it matters, 1 line> | <confidence> | <source link>`. Route per `severity_routing`; honor quiet_hours. Email mode `draft` → Gmail create_draft; `send` only if config says so. Slack → DM to configured target. Push → PushNotification. Always write the file copy. Mask account numbers. Never claim an alert was sent unless the tool call succeeded.

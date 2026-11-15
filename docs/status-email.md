# Status e-mail

Subject `[Investassist] Status - YYYYMMDD` (today, no dashes, e.g. 20261115). Body (plain text): what was done in the session, own total with change since the last status, by platform / asset class / currency, other owners, active alerts, data quality, Drive folder link. Rule: RULES.md G. Skill: `send-status-email`. Script: `scripts/status_email.py`.

Opt-in: `config/alerts.yaml` -> `status_email` (default `enabled: false`). The `setup` skill asks whether to send, takes the address, then asks again to confirm the address (the mail contains sensitive totals) before `status_email.py enable --to ADDR --confirmed`. `status_email.py check` must exit 0 before anything is sent. `status_email.py disable` turns it off.

The mail is sent by the agent with a mail connector (Gmail `send_message`); the script only builds the text and keeps the baseline (`data/publish/status_snapshots.csv`) for the "change since last status" lines. The privacy scan blocks IBANs, account numbers with bank code, 10+ digit runs and deny-list terms (`local/publish_denylist.txt`).

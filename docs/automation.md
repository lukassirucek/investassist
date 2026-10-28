# Automation

- **Daily run** (`prompts/daily.md` -> skill `daily-scan`): refresh indexes and FX, read mail, search news by watchlist tier, verify and log signals, top-holding outlook, digest + dashboard, route alerts.
- **Weekly run** (`prompts/weekly.md` -> `portfolio-report` + weekly watch skills): concentration vs limits, resolved signals, track record.
- **Mail** is read-only; every relevant mail becomes a row in `data/ledger/mail_events.csv`; `review`/`urgent` rows show on the dashboard.
- **Statement reminders:** in the weekly run, list platforms whose index is older than 35 days.
- **Event-driven items** (central-bank meeting days, earnings) come from dated catalysts in the outlook and signals; the dashboard shows the next 14 days.
Setup and mechanisms: `docs/scheduling.md`.

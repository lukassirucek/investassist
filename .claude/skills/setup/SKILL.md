---
name: setup
description: Onboarding wizard for a fresh clone - create the private workspace, ask who the investor is, inventory the exports, build a parser or typed index per platform, set reference data and FX, mail routes, alerts, run the first pipeline and schedule daily and weekly monitoring. Use on "set up", "get started", or when config/profile.yaml or data/index is missing.
---
Goal: from a fresh clone and the user's own exports to a working daily dashboard plus scheduled monitoring. Ask only what the files cannot tell you. Never invent numbers.

1. **Workspace.** `python3 scripts/init_workspace.py` (safe to rerun). It creates `data/`, `local/`, `config/*.yaml` from the examples and `CLAUDE.local.md`. If the user only wants a look: `python3 scripts/init_workspace.py --demo`, show the dashboard, stop.
2. **Profile** (one AskUserQuestion, up to 4 questions): owner name; base currency (all totals); country (local central bank, housing, tax wrappers); language and timezone. Write `config/profile.yaml`. Ask separately whether other people's accounts (child, partner) appear in the exports - they get their own `owner` and stay out of the owner's totals.
3. **Inventory.** List `data/inbox/` (ask the user to drop every export, statement, screenshot or CSV there; sub-folders per platform are fine). For each file name the platform, type and period. Anything held without a file (physical gold, a platform with no export, a P2P overview) is typed later with `manual_index.py`. Show the list, ask for what is missing.
4. **One index per platform.** For each platform choose:
   - platform listed in `parsers/README.md` -> run that parser (register it in `config/sources.yaml`); platform with a typed template in `examples/typed/` -> fill it and run `manual_index.py`;
   - other machine-readable export (CSV, XLSX, text PDF) -> run `build-parser` (writes `local/parsers/<platform>_index.py`, confirms the column mapping on a first sample, registers it in `config/sources.yaml`);
   - screenshot or typed list -> `ingest-screenshot` / `ingest-manual` (uses `scripts/manual_index.py`);
   - crypto -> `ingest-crypto`.
   Archive each original to `data/raw/<platform>/<YYYY-MM>/` (move, never delete). Result: `data/index/<platform>.positions.csv` + `.index.md` per `docs/index-spec.md`. Check each index total against the platform's own total.
5. **FX.** For every currency that is not the base: look up a dated rate with a source (WebSearch/WebFetch) and write it with `python3 -I scripts/fx_set.py --date D USD=.. EUR=..` (units of base currency per 1 unit).
6. **Reference data.** `python3 -I scripts/build_master_index.py data/index data/fx/fx_latest.csv` then `python3 -I scripts/build_exposure_map.py`. For each row in `data/exposure/unmapped.csv`: identify the instrument from its ISIN with a web search (never from the ticker alone) and add it with `scripts/instruments_add.py` (columns in its docstring). Rerun until `unmapped` is empty. Add a `platform:<platform>:<asset_class>` row for loans and cash.
7. **Mail** (optional). If the agent has a read-only mail connector: ask which senders/addresses carry platform mail, write the routes into `config/sources.yaml` (`mail.routes`; one query per source, e.g. `from:` or `to:`; forwarded mail may need `to:`), test one query, then follow `ingest-email` for a 30-day backfill. No connector -> skip, say so.
8. **Alerts and limits.** Ask where alerts should go (file only is the default; email draft, Slack, push need a target) and write `config/alerts.yaml`. Ask for position limits (max single instrument, platform, speculative share) and a monthly outflow for a cash-runway line; write `config/playbook.yaml`. Add anything the user wants watched but does not own to `config/watchlist.yaml`.
9. **First run.** `python3 scripts/pipeline.py`, then render-check: `python3 -I scripts/check_dashboard_html.py data/reports/<date>/dashboard.html /tmp/shots` (needs `playwright`; skip if absent). Do one `daily-scan` with real news so signals and the top-holding outlook exist. Show the user the dashboard.
10. **Schedule.** Run `schedule-monitoring`.
11. **Remember.** Write `CLAUDE.local.md` (git-ignored): owner and other owners, base currency, tax wrappers, language, exclusions, anything unusual about their platforms, the parsers that exist. Add the platform quirks learned to `local/notes.md`.
12. Report in <= 8 lines: platforms indexed (with totals and reconciliation status), open gaps, what is scheduled and when, where the dashboard is.

Rules: originals are archived, never edited; the user's numbers are the source of truth; if a total does not reconcile, say the gap and ask - do not fix. Nothing personal is committed: `git status` must show no `data/`, `local/`, `config/*.yaml`.

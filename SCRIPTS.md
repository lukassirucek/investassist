# Scripts catalogue

Every script in `scripts/` is listed here (RULES.md section A). **Check this file before writing a script**; extend a close match with a parameter instead of adding a new one; update the entry when a script changes. Verify with `scripts/check-rules.sh`. Ready-made platform parsers: `parsers/README.md`. The user's own scripts: `local/scripts/`, listed in `local/SCRIPTS.local.md` (same entry format).

Conventions: run from the repo root as `python3 -I scripts/<name>.py`. Money columns end in `_base`. Full usage is in each script's docstring (`python3 scripts/<name>.py --help` where supported).

Entry: **Purpose** · **Usage** · **Reads/writes** · **Side effects**

## Workspace and pipeline
### `init_workspace.py`
**Purpose:** create the private workspace in a fresh clone (folders, `config/*.yaml` from the examples, `CLAUDE.local.md`, history/knowledge/memory scaffolding); `--demo` loads synthetic data and builds a demo dashboard. **Usage:** `python3 scripts/init_workspace.py [--demo]`. **Writes:** `data/`, `local/`, `reports/`, `config/*.yaml`, `history/`, `knowledge/`, `memory/`, `KNOWLEDGE.md` (all git-ignored). Never overwrites an existing file.
### `pipeline.py`
**Purpose:** the deterministic daily steps in order (master index, exposure, watchlist, digest, outlook list, dashboard). **Usage:** `python3 scripts/pipeline.py [YYYY-MM-DD] [--no-dashboard]`. **Writes:** `data/**`, `data/reports/<date>/`.
### `common.py`
**Purpose:** shared helpers (profile: `OWNER`, `BASE`, `DEMO` from `config/profile.yaml`). Imported by the others, not run directly.
### `htmlkit.py`
**Purpose:** shared HTML/CSS pieces for generated pages. Imported by `build_dashboard_html.py`, not run directly.

## Ingestion and reference data
### `manual_index.py`
**Purpose:** typed or transcribed holdings CSV to a per-platform index. **Usage:** `python3 -I scripts/manual_index.py <input.csv> [out_dir=data/index]`. **Writes:** `data/index/<platform>.positions.csv` + `.index.md` (contract `docs/index-spec.md`). Idempotent.
### `build_master_index.py`
**Purpose:** concatenate all platform indexes and convert to the base currency. **Usage:** `python3 -I scripts/build_master_index.py [index_dir] [fx_csv]`. **Writes:** `data/index/master.positions.csv`, `master.index.md`.
### `fx_set.py`
**Purpose:** write dated FX rates (base units per 1 unit). **Usage:** `python3 -I scripts/fx_set.py [--date D] USD=0.92 GBP=1.17`. **Writes:** `data/fx/fx_latest.csv`.
### `instruments_add.py`
**Purpose:** add or replace one classified instrument without hand-editing CSV. **Usage:** see docstring (`--ids --name --class --sector ...`). **Writes:** `data/reference/instruments.csv`.
### `build_exposure_map.py`
**Purpose:** join master index with instrument reference and FX; exposure tables by sector, region, materials, themes. **Usage:** `python3 -I scripts/build_exposure_map.py`. **Writes:** `data/exposure/*` incl. `unmapped.csv`.
### `build_watchlist.py`
**Purpose:** tiered news-search queries from the held instruments. **Usage:** `python3 -I scripts/build_watchlist.py`. **Writes:** `config/watchlist.generated.yaml`, `data/exposure/watchlist_queries.csv`.

## Monitoring and reports
### `signals.py`
**Purpose:** signal log, impact projection, daily digest. **Usage:** `python3 -I scripts/signals.py ingest <json> | digest [date] | project`. **Writes:** `data/signals/`, `data/reports/<date>/daily_digest.md`.
### `outlook.py`
**Purpose:** top-N holdings outlook (selection, validation, track record). **Usage:** `python3 -I scripts/outlook.py top|ingest|missing|due|outcome|score`. **Writes:** `data/outlook/`.
### `mail_events.py`
**Purpose:** log of what platform e-mails told us. **Usage:** `python3 -I scripts/mail_events.py add|list|last`. **Writes:** `data/ledger/mail_events.csv`.
### `build_dashboard_html.py`
**Purpose:** daily dashboard page. **Usage:** `python3 -I scripts/build_dashboard_html.py [date]`. **Writes:** `data/reports/<date>/dashboard.html`, `dashboard.artifact.html`.
### `check_dashboard_html.py`
**Purpose:** render-check the dashboard with headless Chromium (needs `playwright`). **Usage:** `python3 scripts/check_dashboard_html.py <dashboard.html> <out_dir>`.

## Working memory and process (RULES.md B, C, D, E)
### `prompt-log.py`
**Purpose:** prompt history (RULES.md section C): `history/prompts-<who>-YYYYMMWW.md`, summaries, recall, agent exchanges. **Usage:** `python3 scripts/prompt-log.py <add|summarize|exchange|show|path|hook|hook-agent|backfill-model> [options]`.
- `add --who WHO --prompt TEXT|- [--from NAME] [--summary TEXT] [--time "YYYY-MM-DD HH:MM"] [--model ID]` (`WHO` = `user` or an agent name; summary defaults to `_pending_`).
- `summarize --who WHO --summary TEXT [--date D] [--model ID]` fills the last `_pending_` summary and corrects its `**Model:**` line.
- `show [--who WHO|all] [--date D] [--since D] [--until D] [--full]`; `path [--who] [--date]`; `backfill-model`.
- `exchange --to AGENT --from SENDER --prompt TEXT|@file [--response TEXT|@file] [--model ID] [--from-model ID]` logs an agent communication in full (C8).
- `hook` (UserPromptSubmit) and `hook-agent` (PostToolUse Task|Agent|SendMessage, SubagentStop): JSON on stdin, never fail or block.
**Example:** `python3 scripts/prompt-log.py show --since 2026-10-20`. **Model line:** `--model`, else env `PROMPT_LOG_MODEL`, hook data, transcript, `.claude/settings.json`, else `unknown`. **Side effects:** writes `history/`; redacts API keys, IBANs and card-like numbers; user name in headers from env `PROMPT_LOG_USER` or `owner` in `config/profile.yaml`.
### `knowledge-find.py`
**Purpose:** look up persisted reference facts before researching (B1). **Usage:** `python3 scripts/knowledge-find.py TERM [TERM...]`; prints `[fresh|STALE] file - title - summary`, exit 1 if nothing found.
### `knowledge-add.py`
**Purpose:** persist researched content to `knowledge/<slug>.md` and the `KNOWLEDGE.md` index (B2). **Usage:** `... | python3 scripts/knowledge-add.py --title T --query Q --source URL [--source URL] --summary "..." [--tags a,b] [--ttl-days 30|180] [--update]`. **Side effects:** writes `knowledge/`, `KNOWLEDGE.md` (created if missing).
### `memory-handover.py`
**Purpose:** handover between sessions or tools (E, D4). **Usage:** `python3 scripts/memory-handover.py write --from F --to T --summary S [--decision|--wip|--blocker|--next|--note X]... | status [--for TOOL] | read | ack --by TOOL`. **Side effects:** replaces `memory/HANDOVER.md`, archives the previous in `memory/handovers/`.
### `memory-audit.py`
**Purpose:** find Claude memory stored outside the project; `--import` copies it into `memory/claude/`. **Usage:** `python3 scripts/memory-audit.py [--import]`; exit 1 if something is found.
### `check-rules.sh`
**Purpose:** verify RULES.md compliance (scripts documented, parsers listed, knowledge indexed, hooks wired, `.gitignore` entries, no local files tracked, history entries carry a model). **Usage:** `scripts/check-rules.sh`; exit 0 = ok.

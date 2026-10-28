# Architecture

```
exports / screenshots / typed lists -> data/inbox -> parser (local/parsers) or manual_index.py
   -> data/index/<platform>.positions.csv  -> build_master_index.py (+ fx) -> master.positions.csv
   -> build_exposure_map.py (+ data/reference/instruments.csv) -> data/exposure/holdings_enriched.csv
agent: mail + news + outlook -> signals.json / calls.json -> signals.py ingest / outlook.py ingest
   -> data/signals/signals.csv, data/outlook/*, data/ledger/mail_events.csv
   -> signals.py digest, outlook.py top, build_dashboard_html.py -> data/reports/<date>/{daily_digest.md,dashboard.html}
```
- **Scripts** (tracked, generic) do all arithmetic and rendering; **skills** tell the agent what to do and when; **config/*.yaml** (private) holds profile, sources, alert routing, playbook limits, watchlist.
- **Signals** carry tags (`theme:`, `raw:`, `region:`, `name:`, `class:`, `sector:`) matched against the exposure map; impact = matched value x an explicit % range (a scenario, not a forecast); action candidates come from `config/playbook.yaml`.
- **Outlook:** per top holding, sourced drivers (direction, weight 1-3). Score = sum of signed weights; lean up if >= 3, down if <= -3, else neutral; evidence capped by the number of sourced drivers and distinct domains. Calls are logged; after the horizon the realised move is recorded and hit rates are shown.
- **Overlay model:** tracked = code, skills, docs, examples; ignored = everything personal. Personal parsers live in `local/parsers/`, personal skills as `.claude/skills/local-*`.
- **Working memory (local, git-ignored):** `RULES.md` defines five mechanisms. Scripts registry (`SCRIPTS.md`, `local/SCRIPTS.local.md`); researched reference facts (`knowledge/`, index `KNOWLEDGE.md`, TTL-based freshness); prompt history (`history/`, one file per actor per week, written by a hook, model on every entry); memory (`memory/claude|codex|shared`, index `MEMORY.md` each, Claude `autoMemoryDirectory` points there); handovers between sessions or tools (`memory/HANDOVER.md`). Only the README of each folder is tracked; `scripts/init_workspace.py` creates the rest; `scripts/check-rules.sh` verifies it.

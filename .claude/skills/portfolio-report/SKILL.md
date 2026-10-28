---
name: portfolio-report
description: Weekly (or on-demand) portfolio report - distribution by platform/class/sector/geography, concentrations vs playbook limits, the week's signals, review candidates, data gaps. Use for the weekly run or "portfolio report".
---
1. Rebuild: `python3 scripts/pipeline.py --no-dashboard` (master, exposure, watchlist, digest, outlook shortlist). Refresh FX if older than 7 days.
2. Read `data/exposure/exposure_map.md`, `holdings_enriched.csv`, `data/signals/signals.csv`, `config/playbook.yaml` and the previous `data/reports/*/portfolio_report.md`.
3. Write `data/reports/<date>/portfolio_report.md`: where the money is (platform, class, currency); distribution (sector, region, raw material, theme); concentrations vs playbook limits (status ok / at / over); the week's signals (new, resolved, catalysts in the next 14 days with exposure in base currency); change vs the previous report; review candidates (trim/simplify) and gaps (add) as options; open data items; index staleness per platform.
4. Rules: own portfolio only (other owners excluded); base currency with native currency per position; label FACT / INFERENCE / HISTORICAL PATTERN; never invent numbers; suggestions are options for review, never orders; end with "Not financial advice".

---
name: ingest-manual
description: Ingest holdings the user types in or that have no export (an app that blocks screenshots, a P2P overview, physical assets). Use when the user lists positions as text or a platform has no machine-readable file.
---
1. Save the typed input verbatim under `data/raw/<platform>/<YYYY-MM>/`. Typed data is the source of truth: never reformat numbers silently.
2. Convert to the `manual_index.py` input CSV (columns in its docstring: platform, account, portfolio_type, asset_class, instrument_id, symbol, name, country, units, price, cost, value, ccy, valuation_date, owner, status, confidence, notes, interest_rate_pct; a row with asset_class `total` carries the platform's own total for reconciliation). Blank = unknown.
3. A typed row such as `<units>x <name> / <number> <ccy>, total <value>`: check units x number against the total. If they differ the number is probably the average purchase price and the total the current value; state the assumption in `notes` and confirm with the user (AskUserQuestion), do not guess.
4. Totals typed in another currency may include cash and need FX: never back out cash or FX yourself; ask.
5. `python3 -I scripts/manual_index.py <input.csv> data/index` writes `data/index/<platform>.positions.csv` + `.index.md` (confidence `medium`). Then `master-index`, `build-exposure-map`.
6. Match ISIN/symbol with other indexes when the same instrument exists there and say so in `notes`.

---
name: build-parser
description: Write a parser for one platform's export (CSV, XLSX, text PDF) that produces the standard per-platform index. Use when ingest-router meets a file format with no registered parser, or when the user adds a new platform.
---
Output contract: `docs/index-spec.md`. Parser lives in `local/parsers/<platform>_index.py` (git-ignored, personal), starts from `templates/parser_template.py`, usage `python3 -I local/parsers/<platform>_index.py <input_path_or_dir> [out_dir=data/index]`, writes `data/index/<platform>.positions.csv` + `<platform>.index.md`.

0. **Check the catalogue first.** `parsers/README.md` lists ready-made parsers (Revolut, Portu, Indigo, Raiffeisenbank, Investown, Golden Gate) and `docs/platform-notes.md` the typed route for others (Zonky, Patria, ČSOB Investice, Air Bank, physical gold, bank balances). If the platform is there, run that parser or fill the template instead of writing a new one; only write a new parser when the layout differs (say what differs).
1. **Look at the real file.** Read 30 rows or the first pages: encoding, delimiter, decimal comma, date format, header row (often not row 1), one row per position or per transaction, multiple currencies, summary rows. PDFs: `pdftotext -layout` first; if no text layer, treat as screenshot (`ingest-screenshot`).
2. **Decide the data type.** Holdings snapshot -> one index row per position. Transaction history -> net units per instrument (buys minus sells), cost = net invested, realised P&L and dividends where present; value only if the file has prices, otherwise leave `value` blank and say so in the index (the owner can add a typed valuation via `manual_index.py`). Cash balances -> asset_class `cash`.
3. **Show the proposed mapping** (source column -> index column, 5 sample rows, anything dropped, any assumption such as "number = average purchase price") and confirm it with the user (AskUserQuestion) the first time. Never guess on money data.
4. **Write the parser** from the template: pure stdlib or pandas/openpyxl if installed; deterministic and idempotent; no network; masks account numbers to the last 4 digits; a `confidence` per row (`high` statement/export, `medium` typed/screenshot); a `raw_ref` note (file + row) in `notes`.
5. **Test.** Run it; compare `sum(value)` and unit counts with the platform's own totals or the file's closing balance; list every mismatch in `.index.md` under a "Reconciliation" heading with the gap. Re-run to prove the output is identical (no duplicates).
6. **Register** in `config/sources.yaml` (`type`, `formats`, `detect`, `parser`, `report_ccy`, `confirmed: true` after the user agrees). Save platform quirks in `local/notes.md`.
7. Archive the input to `data/raw/<platform>/<YYYY-MM>/`, then run `master-index` and `build-exposure-map`.
If the same platform is shared by many users, mention that a generic version could go to `docs/platform-notes.md` (sanitised: no personal data) via a pull request.

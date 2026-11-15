---
name: ingest-screenshot
description: Extract holdings/balances from screenshots of banking or investment apps into a typed input for manual_index.py.
---
Read the image directly (view it; OCR text from a connector is only for triage, it scrambles reading order and may come back empty). Output a table of what is visible with a confidence per row; screenshots are lossy -> `confidence=medium`, `notes` carries the file name. If any figure is cropped, ambiguous or conflicts with existing data, show the table and confirm with the user (AskUserQuestion) before writing.
- Screenshots are point-in-time holdings; do not synthesise transactions from them. A later statement or export supersedes the screenshot rows.
- App list screens often truncate units; overlapping rows across screenshots: keep the later one; check sum(positions) + cash against the total shown in the app.
- Transcribe to a CSV in the `manual_index.py` format (see `ingest-manual`), archive PNG + CSV in `data/raw/<platform>/<YYYY-MM>/`, then build the index with `manual_index.py`.
- A file from a cloud drive connector can be too large for context and saved to disk as base64 JSON: decode it to PNG first.

## App screenshot formats seen (typed route -> `manual_index.py`, confidence medium)
- ČSOB Smart (bank): account list; credit card shows AVAILABLE -> used = limit - available, `loan_liability`, negative value; a business account (Podnikatelský) gets its own `owner` value. Template `examples/typed/csob_bank.example.csv`.
- Raiffeisenbank mobile app (bank, platform `raiffeisen_bank`): same rules. Template `examples/typed/raiffeisen_bank.example.csv`. Not the same as Raiffeisenbank Investice.
- Patria Finance app: screens are now readable (earlier blocked); units, average purchase price, current value; keep regular/DIP via `portfolio_type`.
- Raiffeisen Investing and Portu apps: screens accepted when no statement exists; Portu statement PDFs are named `Vypis_z_uctu_YYYY_MM.pdf`.
- Revolut: list screens + `CASH_<ccy>` row for `revolut_index.py --screens`.
Never write account numbers (last 4 digits only), IBANs or custom pocket names.

## iPhone app screenshots (details: docs/platform-notes.md, section "iPhone app screenshots")
- Air Bank (bank cash `airbank_bank`, stocks `airbank`, Zonky line, Portu line = same as `portu`), mBank (`mbank`, totals only), Golden Gate (Komoditní + Bitcoinový účet -> `golden_gate`, `physical_gold` price), Indigo (total + activity only).
- Newer TOTAL for a statement-based platform (Portu, Indigo) -> `scripts/marks_index.py`, never invented positions. Run order: platform indexes, marks, `build_master_index.py`.
- Foreign-currency accounts: native currency in `ccy`; overdraft facilities ("včetně kontokorentu") are not cash.
- App P&L figures that do not reconcile with the value (Indigo) are not stored.

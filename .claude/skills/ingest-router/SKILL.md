---
name: ingest-router
description: Entry point for importing any statement, export, screenshot or e-mail into the portfolio. Use when files appear in data/inbox/ or the user says "ingest", "import", "update portfolio".
---
1. Optional drop zone: if `config/sources.yaml` has `drive.folder_url` and a Drive connector exists, list the folder, download files not yet in `data/raw/` (match by name + size/modified) into `data/inbox/`. Leave originals untouched.
2. List `data/inbox/`. For each file detect the platform (filename, header row, logo/text, sender) using `config/sources.yaml`.
3. Archive the original to `data/raw/<platform>/<YYYY-MM>/` (move, never delete).
4. Dispatch: registered parser in `sources.yaml` -> run it; platform in `parsers/README.md` -> that parser; typed template in `examples/typed/` -> `manual_index.py`; CSV/XLSX/text-PDF with no parser -> `build-parser`; image -> `ingest-screenshot`; typed list or platform without export -> `ingest-manual`; crypto -> `ingest-crypto`; mail -> `ingest-email`.
5. Unknown platform or `confirmed: false` -> show the first 5 rows and the proposed mapping, confirm with the user (AskUserQuestion) before writing anything.
6. After all files: reconcile against the platform's own totals, append a line to `data/ledger/ingest_log.md`, print a 5-line summary (files, rows added, duplicates, mismatches, open questions), then `master-index`, then `build-exposure-map` for any new instrument.
Always set `portfolio_type` when a platform holds several wrappers (regular / retirement / tax-advantaged); never merge them in tax-relevant output. Contract: `docs/index-spec.md`.

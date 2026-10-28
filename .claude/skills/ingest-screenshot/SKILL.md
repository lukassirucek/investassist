---
name: ingest-screenshot
description: Extract holdings/balances from screenshots of banking or investment apps into a typed input for manual_index.py.
---
Read the image directly (view it; OCR text from a connector is only for triage, it scrambles reading order and may come back empty). Output a table of what is visible with a confidence per row; screenshots are lossy -> `confidence=medium`, `notes` carries the file name. If any figure is cropped, ambiguous or conflicts with existing data, show the table and confirm with the user (AskUserQuestion) before writing.
- Screenshots are point-in-time holdings; do not synthesise transactions from them. A later statement or export supersedes the screenshot rows.
- App list screens often truncate units; overlapping rows across screenshots: keep the later one; check sum(positions) + cash against the total shown in the app.
- Transcribe to a CSV in the `manual_index.py` format (see `ingest-manual`), archive PNG + CSV in `data/raw/<platform>/<YYYY-MM>/`, then build the index with `manual_index.py`.
- A file from a cloud drive connector can be too large for context and saved to disk as base64 JSON: decode it to PNG first.

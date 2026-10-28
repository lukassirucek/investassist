---
name: master-index
description: Answer "what do I hold through <platform> / overall?" from the index files, and rebuild the master index after any platform index changes.
---
1. Per-platform indexes: `data/index/<platform>.positions.csv` (+ `.index.md`); contract `docs/index-spec.md`.
2. Rebuild: `python3 -I scripts/build_master_index.py data/index data/fx/fx_latest.csv` -> `master.positions.csv`, `master.index.md`. Base-currency totals need a dated FX file (`scripts/fx_set.py`, source cited); never guess FX.
3. Questions: read the relevant `*.index.md` first (totals + caveats), query the CSV for detail. Report native currency per row, base currency in totals. State caveats that change the answer (no market values, unverified units, stale statement) in one line.
4. Platform without an index -> say so and offer to ingest. After any ingest: rebuild the platform index, then the master.

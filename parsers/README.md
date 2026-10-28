# Ready-made platform parsers

Each parser reads the platform's real export and writes the standard index (`data/index/<platform>.positions.csv` + `.index.md`, format in `docs/index-spec.md`). They reconcile against the platform's own totals and list every mismatch; nothing is fixed silently. Run from the project root: `python3 -I parsers/<name>_index.py --help`.

| Platform | Parser | Input | Notes |
|---|---|---|---|
| Revolut (stocks, ETFs, crypto) | `revolut_index.py` | "Consolidated statement" **xlsx** (Investment Services); optional transcribed app screens for market values | needs `openpyxl`; `--aliases` JSON for confirmed corporate actions; works for any report currency |
| Portu (CZ robo-advisor) | `portu_index.py` | monthly statement **PDF or text** + a small manifest CSV | needs `pdftotext` for PDFs; several accounts and owners (children) per manifest |
| Indigo / Patria Finance (CZ robo-advisor) | `indigo_index.py` | quarterly statement **e-mail saved as HTML** | cost basis unknown from one quarter |
| Raiffeisenbank Investice (CZ) | `raiffeisen_index.py` | "Výpis z majetkového účtu" **PDF** per contract | needs `pdftotext`; `--dip` marks DIP contracts; `--cash` adds cash |
| Investown (CZ crowdlending) | `investown_index.py` | two CSVs transcribed from the app screens | no export exists; template in `examples/typed/` |
| Golden Gate (CZ gold + bitcoin) | `golden_gate_index.py` | one CSV of figures typed from the platform | derives accumulated grams from the "remaining to complete brick" figure |

Everything else (Zonky, Patria brokerage, ČSOB Investice, Air Bank Investice, physical gold, bank balances, any other platform) uses the generic typed route: copy the matching `examples/typed/*.example.csv` to `data/raw/<platform>/`, fill in your figures and run `python3 -I scripts/manual_index.py <file> data/index`.

The parsers were written against real exports (as of Oct 2026) and checked row by row against hand-built indexes; a platform may change its layout, in which case the parser stops with a clear message rather than guessing. Fix or extend with the `build-parser` skill and send a pull request (sanitised: no personal data in tests or examples).

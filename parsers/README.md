# Ready-made platform parsers

Each parser reads the platform's real export and writes the standard index (`data/index/<platform>.positions.csv` + `.index.md`, format in `docs/index-spec.md`). They reconcile against the platform's own totals and list every mismatch; nothing is fixed silently. Run from the project root: `python3 -I parsers/<name>_index.py --help`.

| Platform | Parser | Input | Notes |
|---|---|---|---|
| Revolut (stocks, ETFs, crypto, current-account pockets) | `revolut_index.py` | "Consolidated statement" **xlsx** (Investment Services only, whole history) or **csv v2** (all products: Current Accounts blocks + investments + crypto, period-limited); optional transcribed app screens for market values | xlsx needs `openpyxl`, csv needs nothing; a statement that starts after the brokerage opening date is PARTIAL -> written to `revolut.partial.*`, never the master index (`--allow-partial` to override); `--pockets` adds current-account cash rows; `--aliases` JSON for confirmed corporate actions; any report currency |
| Portu (CZ robo-advisor) | `portu_index.py` | monthly statement **PDF or text** + a small manifest CSV | needs `pdftotext` for PDFs; several accounts and owners (children) per manifest |
| Indigo / Patria Finance (CZ robo-advisor) | `indigo_index.py` | quarterly statement **e-mail saved as HTML** | cost basis unknown from one quarter |
| Raiffeisenbank Investice (CZ) | `raiffeisen_index.py` | "Výpis z majetkového účtu" **PDF** per contract | needs `pdftotext`; `--dip` marks DIP contracts; `--cash` adds cash |
| Investown (CZ crowdlending) | `investown_index.py` | two CSVs transcribed from the app screens | no export exists; template in `examples/typed/` |
| Golden Gate (CZ gold + bitcoin) | `golden_gate_index.py` | one CSV of figures typed from the platform or its **iPhone app screenshots** (Komoditní účet, Bitcoinový účet) | derives accumulated grams from the "remaining to complete brick" figure; optional `btc_account / price_<ccy>` row gives BTC a market value; `--asof` sets the date |

Totals-only platforms: when an app screenshot gives only a newer TOTAL for a platform whose positions come from a statement (Portu, Indigo), `scripts/marks_index.py` adds a dated valuation mark (`examples/typed/marks.example.csv`) instead of inventing positions.

Everything else (Zonky, Patria brokerage, ČSOB Investice, Air Bank Investice and Air Bank/mBank/Raiffeisen/ČSOB bank balances, physical gold, any other platform) uses the generic typed route: copy the matching `examples/typed/*.example.csv` to `data/raw/<platform>/`, fill in your figures and run `python3 -I scripts/manual_index.py <file> data/index`.

The parsers were written against real exports (as of Oct 2026) and checked row by row against hand-built indexes; a platform may change its layout, in which case the parser stops with a clear message rather than guessing. Fix or extend with the `build-parser` skill and send a pull request (sanitised: no personal data in tests or examples).

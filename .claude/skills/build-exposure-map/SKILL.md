---
name: build-exposure-map
description: Classify every held instrument (sector, industry, headquarters, revenue regions, raw materials, themes) and build exposure tables in the base currency. Run after any index change or new instrument.
---
Reference data: `data/reference/instruments.csv` (columns `ids|name|class|sector|industry|sub_industry|hq|revenue_regions|raw_materials|themes`; `ids` = ISINs/symbols/names used by the indexes, separated by `|`; `platform:<platform>:<asset_class>`, `cash:<ccy>` and `cash` match whole groups; list-valued columns use `;`). Template rows: `examples/reference/instruments.example.csv`.
Run `python3 -I scripts/build_exposure_map.py` -> `data/exposure/holdings_enriched.csv`, `exposure_<dimension>.csv`, `exposure_map.md`, `unmapped.csv`.
For each instrument in `unmapped.csv`: identify it from its ISIN with a web search (never guess from a ticker), add it with `python3 -I scripts/instruments_add.py` (see docstring), rerun. ETF sector look-through uses approximate index weights (INFERENCE; refresh from the provider factsheet quarterly). Raw-material and theme tables overlap (a holding counts fully under each tag) and show dependency, not sensitivity. Revenue regions and raw materials per company are general knowledge: re-verify annually from the annual report.
Own portfolio = the profile `owner`; other owners are reported separately.

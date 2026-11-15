# Drive publish

Outputs (indexes, summaries, dashboard) are copied to the Drive folder `Published` (inside the Investassist Drive folder, next to `Exports`) so they can be read in Drive and Gemini. Rule: RULES.md F. Skill: `publish-to-drive`. Script: `scripts/drive_publish_bundle.py`.

| Drive file | Type | Source |
|---|---|---|
| 00_README | Doc | generated: what, when, caveats |
| 01_master_positions | Sheet | `data/index/master.positions.csv` |
| 02_master_index | Doc | `data/index/master.index.md` |
| 03_platform_indexes | Doc | all `data/index/<platform>.index.md` (not `.partial.`) |
| 04_dashboard_summary | Doc | generated text companion: own total, by platform/class/currency/sector, top 15, exposure map |
| 05_daily_digest | Doc | `data/reports/<day>/daily_digest.md` |
| 07_latest_weekly / 07_latest_alerts | Doc | newest `reports/weekly`, `reports/alerts` |
| 08_dashboard.html | HTML | `data/reports/<day>/dashboard.artifact.html` (Gemini cannot render; use 04) |

Mechanics: names are stable; Drive cannot replace content in place, so a changed file is re-created and the old id trashed; ids live in `data/publish/registry.csv` (git-ignored). The privacy scan blocks IBANs, account numbers with bank code, 10+ digit runs and terms in `local/publish_denylist.txt`. Markdown is converted to Docs as plain text (markup characters show literally); fine for Gemini.
Totals note: the master own total includes valuation marks; the exposure map is statement-based, so it can be lower (the difference is the marks sum; 04 states it).

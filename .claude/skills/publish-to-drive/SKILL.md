---
name: publish-to-drive
description: Publish the current indexes, master, summaries, digest and dashboard to the Google Drive "Published" folder so they are readable in Drive and Gemini. Use after any index/master/report/dashboard rebuild, at the end of ingest, daily-scan and portfolio-report, or when the user says "publish", "upload to drive", "sync drive".
---
Rule: RULES.md section F. Needs a Drive connector (mcp__Google_Drive__*) and the device bridge (the repo is on the user's computer). If either is missing: say so, do not claim anything was published.
1. Make sure the outputs are current: `python3 scripts/pipeline.py [day]` (master, exposure, watchlist, digest, outlook, dashboard) after platform indexes/marks are rebuilt.
2. `python3 -I scripts/drive_publish_bundle.py build [day]`. A failed privacy scan stops here: fix the source (never weaken the scan), rebuild.
3. `python3 -I scripts/drive_publish_bundle.py status --json` -> upload only `new` and `changed`. Folder id = `folder_id` (config `drive.publish_folder_id`; if missing: search the Investassist Drive folder for `Published`, else create it next to `Exports`, then `record _folder ID`).
4. For each file: `device_stage_files` (`<repo>/data/publish/<file>`) -> in the container `sha256sum /mnt/user-data/uploads/<repo-folder>/data/publish/<file>` -> `mcp__Google_Drive__create_file` with `title` = NAME (no extension; `08_dashboard.html` keeps `.html`), `parentId` = folder id, `base64Content` = `sha256:<hex>:<abs path>`, `contentMimeType` = `text/plain` (md -> Google Doc), `text/csv` (-> Google Sheet), `text/html` + `disableConversionToGoogleType: true` (dashboard). Calls are independent: send them in one block.
5. Replacing: Drive cannot overwrite content, so after the new file exists `mcp__Google_Drive__trash_file` the old `drive_id` (trash, not delete), then `python3 -I scripts/drive_publish_bundle.py record NAME NEW_ID`.
6. Verify one Doc with `read_file_content` (content present, as-of date right). Append one line to `data/portfolio/ingest_log.md` (files, as-of, new/changed).
7. Tell the user the folder link and which files changed. Gemini: ask it about `04_dashboard_summary` and `01_master_positions` (the HTML dashboard is not rendered by Gemini).
Never upload anything outside `data/publish/` (no raw statements, screenshots, `local/`, `memory/`). The master includes other owners' rows (owner column), `00_README` says so.

Next: skill `send-status-email` (RULES G), which links this folder.

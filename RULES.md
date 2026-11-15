# RULES

Process rules for every agent working in this repository (Claude Code, Codex, ChatGPT agents, subagents). They apply to every session and prompt. Domain rules (privacy, sources, no trade orders) are the prime rules in `CLAUDE.md`. `history/`, `knowledge/`, `memory/` and `KNOWLEDGE.md` are local and git-ignored: they never leave the machine through git.

## 0. Every surface, every session (NON-NEGOTIABLE)
These mechanisms apply identically in Claude Code (CLI/IDE), Claude desktop / cloud / Cowork sessions (repo reached via the device bridge), Codex and ChatGPT agents. **Hooks exist only in local Claude Code**: on every other surface nothing logs for you, so never assume history or knowledge was written. Run scripts from the project root (`cd` into the project folder; on the bridge: `device_bash`).
1. **Start:** read this file, `CLAUDE.md` / `AGENTS.md`, `memory/HANDOVER.md` if present, `memory/*/MEMORY.md`.
2. **Before writing a script:** `SCRIPTS.md`. **Before researching a reference fact:** `scripts/knowledge-find.py`.
3. **After opening any web source for an answer** (article, forecast, rule, fee, format): `scripts/knowledge-add.py` with URL, publication date, a short summary and the FULL fetched text verbatim (B7), before replying (B2, B6).
4. **Last action of every turn:** `python3 -I scripts/prompt-log.py summarize --who user --prompt "<the user's prompt, verbatim>" --summary "<max 2 lines>" --model "<exact model id>"`. With `--prompt` it creates the entry if no hook logged it and fills the summary if one did. Not optional, not "when asked".
5. **After touching scripts, knowledge, history or memory:** `scripts/check-rules.sh`.
6. **If the project folder is unreachable** (computer not linked, bridge down): say so in the reply and do not claim anything was logged; log on the next session.
7. Never commit or push unless asked (D2).

## A. Scripts
- A1 **Check before writing.** Read `SCRIPTS.md` and `ls scripts/ parsers/ local/scripts/` before writing any script. Extend a close match with a parameter instead of adding a new one.
- A2 **Register every script.** Each file in `scripts/` has a header docstring (purpose, usage, inputs, outputs) and an entry in `SCRIPTS.md`. Parsers are listed in `parsers/README.md`. The user's own scripts live in `local/scripts/` and are listed in `local/SCRIPTS.local.md`.
- A3 **Compute with code.** Arithmetic, joins and parsing are scripts, never prose. Scripts run as `python3 -I` from the repo root.
- A4 **Safe by default.** A script that deletes, overwrites original data or sends something outside the repo does a dry run unless given `--apply`. Originals are archived, never deleted.
- A5 **Verify.** After touching scripts, knowledge, history or memory run `scripts/check-rules.sh`.

## B. Knowledge (researched reference facts)
- B1 **Look up first.** Before researching a reference fact (platform export format, instrument identity by ISIN, tax or product rule, fee schedule, data-source behaviour) run `python3 scripts/knowledge-find.py <terms>`. A `fresh` hit is used and cited; a `STALE` hit is re-checked.
- B2 **Persist what you research.** Every such lookup ends with `scripts/knowledge-add.py` (writes `knowledge/<slug>.md` with title, retrieved, fresh_until, query, sources, tags, and the index line in `KNOWLEDGE.md`). Refresh with `--update`, never duplicate.
- B3 **Freshness.** `--ttl-days 30` for fast-changing facts (fees, tax rules, product terms, central-bank rates), `180` for stable ones (file formats, instrument identity).
- B4 **Not knowledge:** daily news, prices and FX. They are dated signals (`scripts/signals.py`), outlook calls or `scripts/fx_set.py` rows, each with URL and date.
- B5 Cite the knowledge file when you rely on it.
- B6 **Every source you open for an answer is saved**, including analyst forecasts and views (`--ttl-days 30`): URL, publication date, a short summary, the full text (B7), and a note when the source is secondary or marketing. Prices, FX and daily news additionally go to signals / `fx_set.py` (B4). Do this before replying, on every surface.

- B7 **Store the whole page, not a note (owner decision 2026-11-10).** Every time you use WebFetch (or any tool that returns page text), the complete returned text is saved verbatim in the knowledge entry, under `## Full content (verbatim)`; the summary is an addition, never a replacement. Ask WebFetch for the full text (prompt: "Return the complete page text verbatim, no summary"; follow `offset` until the page is complete). Pass the text with `--content-file` or stdin, unchanged: no trimming, rewording or key-fact extraction. One entry per URL (`--content-file` per `--source`). Long pages: first part with `knowledge-add.py`, the rest with `--append`. `knowledge-add.py` rejects content under 1500 chars unless `--allow-short`. In local Claude Code the `PostToolUse` hook `scripts/webfetch-save.py` saves every WebFetch result automatically; then curate that entry with `knowledge-add.py --slug S --update --keep-content` (no second copy). Elsewhere you save it yourself. If a fetch is truncated or blocked, say so in the entry and in the reply.

## C. Prompt history
- C1 **Mechanism.** `history/prompts-<actor>-YYYYMMWW.md` (YYYYMM = year and month of the week's Monday, WW = ISO week), one file per actor per week, actor = `user` or an agent name. Written by `scripts/prompt-log.py`; the `UserPromptSubmit` hook in `.claude/settings.json` logs every user prompt automatically. Agents without hooks call `prompt-log.py add --who user --prompt -`.
- C2 **Entry.** Date and time with offset, `From`/`To` for agent exchanges, `Model`, the exact prompt (secrets, IBANs and card-like numbers are redacted), full response for agents, and a Summary of at most 2 lines.
- C3 **Close the turn.** At the end of every turn run `python3 -I scripts/prompt-log.py summarize --who user --prompt "<the user's prompt, verbatim>" --summary "<max 2 lines>" --model "<your exact model id>"`. `--prompt` makes it work without hooks (desktop/cloud/Codex). In a scheduled run this is the last step.
- C4 **Recall.** `prompt-log.py show --date D | --since D [--who WHO] [--full]` answers "what did I ask last week".
- C8 **Nothing unlogged.** All communication with and between subagents is logged in full (prompt and complete response) in the receiver's file; the sender's file keeps the prompt and a pointer. Hooks (`PostToolUse` Task/Agent/SendMessage, `SubagentStop`) do it for Claude Code; otherwise `prompt-log.py exchange`. Verify the entry exists after each delegation.
- C9 **Model on every entry.** Every entry names the LLM and version that produced the response. The hook guesses; correct it with `--model` (or env `PROMPT_LOG_MODEL`).

## D. Process
- D1 **Session start:** this file, `CLAUDE.md` / `AGENTS.md`, `memory/HANDOVER.md` if pending, then `memory/*/MEMORY.md` indexes. If a handover is pending for you: act on it, then `python3 scripts/memory-handover.py ack --by <tool>`.
- D2 **Never commit or push unless the user asks.** Prefer small diffs. Never commit anything under `data/`, `reports/`, `local/`, `history/`, `knowledge/`, `memory/`, `config/*.yaml`.
- D3 **Ask once** when ambiguous (AskUserQuestion / chat options); in unattended runs take the most reasonable reading and say which.
- D4 **Switching tools or ending a work block:** `python3 scripts/memory-handover.py write --from claude --to codex --summary "..." --next "..."`.

## E. Memory
- E1 **All project memory lives in `memory/`** (`claude/`, `codex/`, `shared/`), not in `~/.claude/projects/...`. `.claude/settings.json` sets `autoMemoryDirectory` to `memory/claude`. If the system prompt names another path, this line overrides it. Do not set `memory:` in subagent frontmatter.
- E2 **Format.** Each folder has a `MEMORY.md` index (one line per memory, at most 200 lines) plus topic files with frontmatter `name`, `description`, `type`, `source`, `updated`. Format in `memory/README.md`.
- E3 **What belongs:** feedback on how the user wants the agent to work, platform quirks learned, decisions and their reason, open items. **Not:** holdings, balances, account numbers, credentials (those are in `data/`), anything already in code or docs, and standing owner rules (those go in `CLAUDE.local.md`).
- E4 **Update, don't duplicate.** Fix or remove a memory that turned out wrong. Facts every agent needs go to `memory/shared/`.
- E5 **Audit.** `python3 scripts/memory-audit.py` reports memory stored outside the project (`--import` copies it in).

## F. Publish to Google Drive (indexes, summaries, dashboards)
- F1 **Every rebuild is published.** After any rebuild of an index, the master, the exposure map, a digest/summary/report or the dashboard, the current set is published to the Drive folder `Published` (config `drive.publish_folder_url`) so the user can read it in Drive and Gemini. Skill `publish-to-drive`; the daily/weekly runs and `ingest-router` end with it.
- F2 **Bundle first, scan always.** `python3 -I scripts/drive_publish_bundle.py build` collects the files into `data/publish/` under stable names (`NN_name`) and runs the privacy scan; if the scan fails nothing is uploaded. Upload only `new` / `changed` files (`status`).
- F3 **Gemini-readable.** Indexes and summaries go as Google Docs, the master positions as a Google Sheet (CSV converted), the dashboard as `.html` PLUS the text companion `04_dashboard_summary` (Gemini does not render HTML).
- F4 **One copy per name.** Drive cannot replace file content in place: upload the new version, trash the old file id, `record NAME ID` (registry `data/publish/registry.csv`). The Drive copies are read-only outputs; never edit or ingest from them.
- F5 **Never publish:** credentials, IBANs, account numbers beyond the last 4 digits, raw statements/exports/screenshots, anything in `data/raw` or `data/inbox`, `local/`, `memory/`, custom account or pocket names (deny-list `local/publish_denylist.txt`). The master contains other owners' rows (owner column); `00_README` says so.
- F6 **Log it.** Append one line to `data/portfolio/ingest_log.md` (files, as-of, new/changed). If Drive is unreachable say so in the reply and do not claim it was published.

## G. Status e-mail
- G1 **Opt-in, double-confirmed.** Status e-mails are OFF until `config/alerts.yaml` `status_email` has `enabled: true` and `confirmed: true` (`python3 -I scripts/status_email.py check` exits 0). They contain sensitive portfolio totals, so nothing is ever sent to an address the user did not type and confirm twice. Never infer an address, never reuse one from another field.
- G2 **When.** At the end of every work block that changed data, indexes, totals, summaries, dashboards or rules (after F, `publish-to-drive`), and after each scheduled daily/weekly run. Skill `send-status-email`.
- G3 **Subject.** `[Investassist] Status - YYYYMMDD`, YYYYMMDD = today's date without dashes in the profile timezone (e.g. `[Investassist] Status - 20261115`). Built by `scripts/status_email.py subject`, not by hand.
- G4 **Content.** What was done in the session (3-10 plain lines the agent writes), updated own total with change since the last status, by platform / asset class / currency, other owners separately, active alerts, data quality (stale platforms, valuation marks), the Drive folder link. Computed by `status_email.py build`, never typed from memory.
- G5 **Safe.** Plain text; no credentials, IBANs, account numbers beyond the last 4 digits (the privacy scan in `build` blocks them), no attachments, no raw statements. A failed scan means no e-mail.
- G6 **Log.** After sending run `status_email.py sent` (stores the baseline for the next "change since" and logs a line). If no mail connector is available or sending fails, say so in the reply; do not claim it was sent.
- G7 **Setup.** The `setup` skill asks whether to enable status e-mails, takes the address, then asks again to confirm the address and the sensitivity before running `status_email.py enable --to ADDR --confirmed`. A user who declines stays disabled.

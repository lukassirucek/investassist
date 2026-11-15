---
name: send-status-email
description: Send the "[Investassist] Status - YYYYMMDD" e-mail (session summary, updated totals, indexes, summaries) to the confirmed recipient. Use at the end of every work block that changed data/indexes/summaries/rules, after daily-scan and portfolio-report, or when the user says "send status".
---
Rule: RULES.md section G. Needs a mail connector that can SEND (Gmail `send_message`; load it with ToolSearch). No connector or send fails -> say so, do not claim it was sent.
1. `python3 -I scripts/status_email.py check`. Exit 1 = status e-mails are not enabled/confirmed: stop silently (do not ask again unless the user raises it or this is the setup skill). Exit 0 prints the recipient.
2. Make sure outputs are current (indexes, marks, `scripts/pipeline.py`) and `publish-to-drive` ran (the e-mail links the Drive folder).
3. Write the session summary to a temp file in `data/publish/` (e.g. `status_summary.txt`): 3-10 plain lines, what changed in this work block (data ingested, rules/scripts added, open gaps). No account numbers, no IBANs, no credentials.
4. `python3 -I scripts/status_email.py build [YYYY-MM-DD] --summary-file data/publish/status_summary.txt` -> prints the subject; body is `data/publish/status_email_<YYYYMMDD>.txt`. A failed privacy scan: fix the summary/source, rebuild; never send around it.
5. Read the body file, then send it as plain text with the printed subject (exactly `[Investassist] Status - YYYYMMDD`) to the recipient from `check`. No attachments, no cc/bcc.
6. `python3 -I scripts/status_email.py sent [YYYY-MM-DD]` (baseline + log). Tell the user in one line: sent to whom, subject, own total.
Never send to any other address, and never enable/confirm on the user's behalf: `enable` only runs after the setup skill's double confirmation (or the user's explicit instruction naming the address).

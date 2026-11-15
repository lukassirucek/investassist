#!/usr/bin/env python3
"""Persist retrieved online content to knowledge/<slug>.md and index it in KNOWLEDGE.md (RULES.md section B). Local only: knowledge/ and KNOWLEDGE.md are git-ignored; created on first use.
The entry holds a short summary AND the FULL fetched text, verbatim (B7): never a note instead of the page.

usage: knowledge-add.py --title T --query Q --source URL [--source URL ...] --summary "1-2 lines"
                        [--tags a,b] [--ttl-days 30] [--slug s] [--update] [--content-file F [--content-file F ...]] [--allow-short]
       knowledge-add.py --slug s --append [--content-file F]      add a further part of a long page to an existing entry
  content     the complete WebFetch/page text, verbatim. stdin by default; with several --source pass one --content-file per source, same order
  --ttl-days  freshness window; 30 for fast-changing topics (fees, tax rules, product terms), 180 for stable ones (file formats, instrument identity)
  --update    overwrite an existing entry (file + index line) instead of failing
  --append    add content to an existing entry (long pages that do not fit one call); no other options needed
  --keep-content with --slug S --update: keep the full text already in the entry (hook-saved), replace title/summary/tags only
  --allow-short  accept content under 1500 chars (only when the page itself is that short)
example: python3 scripts/knowledge-add.py --title "ACME Broker CSV export columns" --query "acme broker transaction export csv columns" \\
           --source https://example.com/help/export --content-file /tmp/acme.txt \\
           --summary "Export has 12 columns; amounts use comma decimals." --tags acme,export --ttl-days 180
"""
import argparse, datetime as dt, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(ROOT, "knowledge")
INDEX = os.path.join(ROOT, "KNOWLEDGE.md")
MIN_CHARS = 1500

def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "entry"

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--title"); ap.add_argument("--query")
ap.add_argument("--source", action="append", default=[]); ap.add_argument("--summary")
ap.add_argument("--tags", default=""); ap.add_argument("--ttl-days", type=int, default=30)
ap.add_argument("--slug"); ap.add_argument("--update", action="store_true"); ap.add_argument("--append", action="store_true")
ap.add_argument("--content-file", action="append", default=[]); ap.add_argument("--allow-short", action="store_true"); ap.add_argument("--keep-content", action="store_true")
a = ap.parse_args()

MARK = "## Full content (verbatim)"
if a.keep_content:  # the full text is already in the entry (saved by scripts/webfetch-save.py): keep it, replace the summary part
    _p = os.path.join(KDIR, (a.slug or "") + ".md")
    if not a.slug or not os.path.exists(_p) or MARK not in open(_p, encoding="utf-8").read(): sys.exit("--keep-content needs --slug of an existing entry with a Full content section")
    parts = [open(_p, encoding="utf-8").read().split(MARK, 1)[1].strip()]; a.allow_short = True
else:
    parts = [open(f, encoding="utf-8").read() for f in a.content_file] if a.content_file else [sys.stdin.read()]
if not all(p.strip() for p in parts):
    sys.exit("no content given (stdin or --content-file)")

if a.append:
    if not a.slug: sys.exit("--append needs --slug")
    path = os.path.join(KDIR, a.slug + ".md")
    if not os.path.exists(path): sys.exit("no such entry: knowledge/%s.md" % a.slug)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n\n### Continued\n\n" + "\n\n".join(p.strip() for p in parts) + "\n")
    print("appended to knowledge/%s.md" % a.slug); sys.exit(0)

for k in ("title", "query", "summary"):
    if not getattr(a, k): sys.exit("--%s is required" % k)
if not a.source: sys.exit("--source is required")
if len(parts) > 1 and len(parts) != len(a.source):
    sys.exit("give one --content-file per --source, in the same order")
if sum(len(p.strip()) for p in parts) < MIN_CHARS and not a.allow_short:
    sys.exit("content is under %d chars: store the full fetched text verbatim, not a note (RULES B7). Use --allow-short only if the page itself is that short." % MIN_CHARS)

slug = a.slug or slugify(a.title)
path = os.path.join(KDIR, slug + ".md")
if os.path.exists(path) and not a.update:
    sys.exit("exists: knowledge/%s.md (use --update to refresh)" % slug)
today = dt.date.today()
fresh = today + dt.timedelta(days=a.ttl_days)
tags = [t.strip() for t in a.tags.split(",") if t.strip()]
os.makedirs(KDIR, exist_ok=True)
fm = "---\ntitle: %s\nretrieved: %s\nfresh_until: %s\nquery: %s\nsources:\n%s\ntags: [%s]\n---\n\n# %s\n\n" % (
    json.dumps(a.title, ensure_ascii=False), today, fresh, json.dumps(a.query, ensure_ascii=False),
    "\n".join("  - " + s for s in a.source), ", ".join(tags), a.title)
blocks = [p.strip() if a.keep_content else "### Source: %s\n\n%s" % (a.source[i] if len(parts) > 1 else ", ".join(a.source), p.strip()) for i, p in enumerate(parts)]
body = "## Summary\n\n%s\n\n## Full content (verbatim)\n\n%s\n" % (" ".join(a.summary.split()), "\n\n".join(blocks))
open(path, "w", encoding="utf-8").write(fm + body)

line = "- [%s](knowledge/%s.md) · retrieved %s · fresh until %s · tags: %s — %s" % (
    a.title, slug, today, fresh, ", ".join(tags) or "-", " ".join(a.summary.split()))
HEADER = ("# Knowledge index\n\nIndex of `knowledge/*.md`: reference facts retrieved from the internet (local, git-ignored). Rules: `RULES.md` section B.\n"
          "Before researching: `python3 scripts/knowledge-find.py <terms>`. Add or refresh with `scripts/knowledge-add.py` (full fetched text, B7).\n\n"
          "Entry: title link · retrieved · fresh until · tags — summary\n\n## Entries")
lines = (open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else HEADER).rstrip("\n").split("\n")
marker = "](knowledge/%s.md)" % slug
for i, l in enumerate(lines):
    if marker in l:
        lines[i] = line
        break
else:
    lines.append(line)
open(INDEX, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote knowledge/%s.md and updated KNOWLEDGE.md" % slug)

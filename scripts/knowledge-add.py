#!/usr/bin/env python3
"""Persist retrieved online content to knowledge/<slug>.md and index it in KNOWLEDGE.md (RULES.md section B). Local only: knowledge/ and KNOWLEDGE.md are git-ignored; created on first use.

usage: knowledge-add.py --title T --query Q --source URL [--source URL ...] --summary "1-2 lines"
                        [--tags a,b] [--ttl-days 30] [--slug s] [--update] [--content-file F]   (content: stdin by default)
  --ttl-days  freshness window; 30 for fast-changing topics (fees, tax rules, product terms), 180 for stable ones (file formats, instrument identity)
  --update    overwrite an existing entry (file + index line) instead of failing
example: echo "retrieved text..." | python3 scripts/knowledge-add.py --title "ACME Broker CSV export columns" \\
           --query "acme broker transaction export csv columns" --source https://example.com/help/export \\
           --summary "Export has 12 columns; amounts use comma decimals." --tags acme,export --ttl-days 180
"""
import argparse, datetime as dt, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(ROOT, "knowledge")
INDEX = os.path.join(ROOT, "KNOWLEDGE.md")

def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "entry"

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--title", required=True); ap.add_argument("--query", required=True)
ap.add_argument("--source", action="append", required=True); ap.add_argument("--summary", required=True)
ap.add_argument("--tags", default=""); ap.add_argument("--ttl-days", type=int, default=30)
ap.add_argument("--slug"); ap.add_argument("--update", action="store_true"); ap.add_argument("--content-file")
a = ap.parse_args()

slug = a.slug or slugify(a.title)
path = os.path.join(KDIR, slug + ".md")
if os.path.exists(path) and not a.update:
    sys.exit("exists: knowledge/%s.md (use --update to refresh)" % slug)
content = open(a.content_file, encoding="utf-8").read() if a.content_file else sys.stdin.read()
if not content.strip():
    sys.exit("no content given (stdin or --content-file)")
today = dt.date.today()
fresh = today + dt.timedelta(days=a.ttl_days)
tags = [t.strip() for t in a.tags.split(",") if t.strip()]
os.makedirs(KDIR, exist_ok=True)
fm = "---\ntitle: %s\nretrieved: %s\nfresh_until: %s\nquery: %s\nsources:\n%s\ntags: [%s]\n---\n\n# %s\n\n" % (
    json.dumps(a.title, ensure_ascii=False), today, fresh, json.dumps(a.query, ensure_ascii=False),
    "\n".join("  - " + s for s in a.source), ", ".join(tags), a.title)
open(path, "w", encoding="utf-8").write(fm + content.strip() + "\n")

line = "- [%s](knowledge/%s.md) · retrieved %s · fresh until %s · tags: %s — %s" % (
    a.title, slug, today, fresh, ", ".join(tags) or "-", " ".join(a.summary.split()))
HEADER = ("# Knowledge index\n\nIndex of `knowledge/*.md`: reference facts retrieved from the internet (local, git-ignored). Rules: `RULES.md` section B.\n"
          "Before researching: `python3 scripts/knowledge-find.py <terms>`. Add or refresh with `scripts/knowledge-add.py`.\n\n"
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

#!/usr/bin/env python3
"""Look up persisted knowledge before searching online (RULES.md section B1). Local only: knowledge/ and KNOWLEDGE.md are git-ignored..

usage: knowledge-find.py TERM [TERM ...]      case-insensitive; matches index lines first, then file contents
output: one line per hit: [fresh|STALE] knowledge/<file>.md — title — summary ; exit 1 if nothing found
example: python3 scripts/knowledge-find.py raiffeisen pdf format
"""
import datetime as dt, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
terms = [t.lower() for t in sys.argv[1:]]
if not terms or terms[0] in ("-h", "--help"):
    print(__doc__); sys.exit(0 if terms else 2)
today = dt.date.today().isoformat()
hits = {}
idx = os.path.join(ROOT, "KNOWLEDGE.md")
for l in (open(idx, encoding="utf-8") if os.path.exists(idx) else []):
    m = re.match(r"- \[(.*?)\]\((knowledge/.*?\.md)\)(.*)", l)
    if m and any(t in l.lower() for t in terms):
        hits[m.group(2)] = (m.group(1), m.group(3).split("—", 1)[-1].strip())
for p in glob.glob(os.path.join(ROOT, "knowledge", "*.md")):
    rel = "knowledge/" + os.path.basename(p)
    if os.path.basename(p) == "README.md" or rel in hits:
        continue
    text = open(p, encoding="utf-8").read()
    if all(t in text.lower() for t in terms):
        t = re.search(r'title: "?(.*?)"?\n', text)
        hits[rel] = (t.group(1) if t else rel, "(content match, not in index summary)")
if not hits:
    print("no match — look it up online, then persist with scripts/knowledge-add.py"); sys.exit(1)
for rel, (title, summ) in sorted(hits.items()):
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    f = re.search(r"fresh_until: (\S+)", text)
    state = "fresh" if f and f.group(1) >= today else "STALE"
    print("[%s] %s — %s — %s" % (state, rel, title, summ))

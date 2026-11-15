#!/usr/bin/env python3
"""PostToolUse hook for WebFetch (local Claude Code only): saves the COMPLETE fetched text verbatim to knowledge/webfetch-<host>-<hash>.md and indexes it in KNOWLEDGE.md (RULES.md B7). Never fails or blocks.

usage: webfetch-save.py hook          JSON on stdin ({tool_input: {url, prompt}, tool_response: ...}); wired in .claude/settings.json
inputs: the WebFetch result as delivered to the hook. Outputs: knowledge/webfetch-*.md (title = URL, summary 'auto-saved, summary pending'), one KNOWLEDGE.md line. A refetch of the same URL replaces the Full content section and the dates, keeping any curated title/summary.
After the hook, the agent curates the entry: knowledge-add.py --slug <slug> --update --keep-content --title ... --query ... --source URL --summary ... (the hook tells it the slug).
"""
import datetime as dt, hashlib, json, os, re, sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR, INDEX = os.path.join(ROOT, "knowledge"), os.path.join(ROOT, "KNOWLEDGE.md")
MARK = "## Full content (verbatim)"

def text_of(r):
    if r is None: return ""
    if isinstance(r, str): return r
    if isinstance(r, list): return "\n\n".join(filter(None, (text_of(x) for x in r)))
    if isinstance(r, dict):
        for k in ("result", "content", "text", "output", "markdown"):
            if r.get(k):
                return text_of(r[k])
        return json.dumps(r, ensure_ascii=False, indent=1)
    return str(r)

def main():
    d = json.load(sys.stdin)
    if d.get("tool_name") not in (None, "WebFetch"): return
    url = (d.get("tool_input") or {}).get("url", "")
    body = text_of(d.get("tool_response")).strip()
    if not url or not body: return
    host = re.sub(r"[^a-z0-9]+", "-", (urlparse(url).hostname or "web").lower()).strip("-")
    slug = "webfetch-%s-%s" % (host, hashlib.sha1(url.encode()).hexdigest()[:8])
    path = os.path.join(KDIR, slug + ".md")
    today = dt.date.today(); fresh = today + dt.timedelta(days=30)
    os.makedirs(KDIR, exist_ok=True)
    if os.path.exists(path):
        old = open(path, encoding="utf-8").read()
        head = old.split(MARK)[0]
        head = re.sub(r"retrieved: \S+", "retrieved: %s" % today, head, 1)
        head = re.sub(r"fresh_until: \S+", "fresh_until: %s" % fresh, head, 1)
        open(path, "w", encoding="utf-8").write(head + MARK + "\n\n### Source: %s\n\n%s\n" % (url, body))
    else:
        title = "WebFetch %s" % url
        open(path, "w", encoding="utf-8").write(
            "---\ntitle: %s\nretrieved: %s\nfresh_until: %s\nquery: %s\nsources:\n  - %s\ntags: [webfetch, auto]\n---\n\n# %s\n\n## Summary\n\nauto-saved by hook, summary pending\n\n%s\n\n### Source: %s\n\n%s\n"
            % (json.dumps(title), today, fresh, json.dumps((d.get("tool_input") or {}).get("prompt", "")[:200]), url, title, MARK, url, body))
        line = "- [%s](knowledge/%s.md) · retrieved %s · fresh until %s · tags: webfetch, auto — auto-saved by hook, summary pending" % (title, slug, today, fresh)
        lines = (open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else "# Knowledge index\n\n## Entries").rstrip("\n").split("\n")
        if not any("](knowledge/%s.md)" % slug in l for l in lines): lines.append(line)
        open(INDEX, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
        "Full WebFetch text saved to knowledge/%s.md (B7). Curate it with: python3 -I scripts/knowledge-add.py --slug %s --update --keep-content --title T --query Q --source %s --summary \"...\"" % (slug, slug, url)}}))

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "hook": main()
        else: print(__doc__)
    except Exception:
        pass
    sys.exit(0)

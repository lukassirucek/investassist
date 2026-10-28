#!/usr/bin/env python3
"""Memory handover between sessions or tools (Claude Code <-> Codex/ChatGPT agent, or one session to the next). RULES.md section E.
Local only: memory/ is git-ignored.

usage:
  memory-handover.py write --from FROM --to TO --summary TEXT [--decision T]... [--wip T]... [--blocker T]...
                           [--next T]... [--note T]... [--body-file F]
  memory-handover.py status [--for TOOL]     one-line state; says if a handover is pending for TOOL
  memory-handover.py read                    print memory/HANDOVER.md
  memory-handover.py ack --by TOOL           mark the pending handover acknowledged
  FROM/TO: claude | codex | user | any agent name. Repeatable options add bullet lines.
example:
  python3 scripts/memory-handover.py write --from claude --to codex --summary "Parser for platform X done, totals reconcile" --next "Add FX for USD"
"""
import argparse, datetime as dt, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, "memory", "HANDOVER.md")
ARCH = os.path.join(ROOT, "memory", "handovers")

def now():
    return dt.datetime.now().astimezone()

def stamp(d):
    z = d.strftime("%z")
    return d.strftime("%Y-%m-%d %H:%M") + " " + z[:3] + ":" + z[3:]

def head():
    meta = {}
    if os.path.exists(H):
        for l in open(H, encoding="utf-8"):
            m = re.match(r"^- (\w+): (.*)$", l.rstrip("\n"))
            if m:
                meta[m.group(1)] = m.group(2)
            elif l.startswith("## "):
                break
    return meta

def git_info():
    try:
        br = subprocess.run(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "no commits"
        dirty = len(subprocess.run(["git", "-C", ROOT, "status", "--porcelain"], capture_output=True, text=True, timeout=10).stdout.splitlines())
        return "%s @ %s, %d uncommitted paths" % (br or "?", sha, dirty)
    except Exception:
        return "unavailable"

def section(title, items, numbered=False):
    if not items:
        return ""
    lines = ["%s %s" % ("%d." % (i + 1) if numbered else "-", t) for i, t in enumerate(items)]
    return "\n## %s\n%s\n" % (title, "\n".join(lines))

def write(a):
    d = now()
    hid = "%s-%s-to-%s" % (d.strftime("%Y%m%d-%H%M"), a.frm, a.to)
    old = head()
    archived = old.get("id") not in (None, "none")
    if archived:
        os.makedirs(ARCH, exist_ok=True)
        dest = os.path.join(ARCH, old["id"] + ".md")
        if not os.path.exists(dest):
            shutil.copy(H, dest)
    text = ("# Handover\n- id: %s\n- from: %s\n- to: %s\n- written: %s\n- status: pending\n- git: %s\n\n## Summary\n%s\n"
            % (hid, a.frm, a.to, stamp(d), git_info(), " ".join(a.summary.split())))
    text += section("Decisions", a.decision) + section("Work in progress", a.wip) + section("Open questions / blockers", a.blocker)
    text += section("Next steps", a.next, True) + section("Notes for the receiver", a.note)
    if a.body_file:
        text += "\n## Details\n" + open(a.body_file, encoding="utf-8").read().strip() + "\n"
    os.makedirs(os.path.dirname(H), exist_ok=True)
    open(H, "w", encoding="utf-8").write(text)
    print("wrote memory/HANDOVER.md (%s)%s" % (hid, "; previous archived in memory/handovers/" if archived else ""))

def status(tool):
    m = head()
    if m.get("id") in (None, "none"):
        print("handover: none written yet"); return
    st = m.get("status", "")
    if st.startswith("pending"):
        if tool and m.get("to") == tool:
            print("PENDING handover for %s (%s, from %s, %s): read memory/HANDOVER.md, act on it, then run: python3 scripts/memory-handover.py ack --by %s"
                  % (tool, m["id"], m.get("from"), m.get("written"), tool))
        else:
            print("handover %s pending for %s (from %s)" % (m["id"], m.get("to"), m.get("from")))
    else:
        print("handover %s: %s" % (m["id"], st))

def ack(tool):
    m = head()
    if not m.get("status", "").startswith("pending"):
        sys.exit("no pending handover")
    if m.get("to") != tool:
        print("note: handover was addressed to %s; acknowledging as %s" % (m.get("to"), tool))
    t = open(H, encoding="utf-8").read()
    t = t.replace("- status: pending", "- status: acknowledged by %s at %s" % (tool, stamp(now())), 1)
    open(H, "w", encoding="utf-8").write(t)
    print("acknowledged")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--from", dest="frm", required=True); w.add_argument("--to", required=True); w.add_argument("--summary", required=True)
    for k in ("decision", "wip", "blocker", "next", "note"):
        w.add_argument("--" + k, action="append", default=[])
    w.add_argument("--body-file")
    s = sub.add_parser("status"); s.add_argument("--for", dest="tool")
    sub.add_parser("read")
    k = sub.add_parser("ack"); k.add_argument("--by", required=True)
    a = ap.parse_args()
    if a.cmd == "write": write(a)
    elif a.cmd == "status": status(a.tool)
    elif a.cmd == "read": sys.stdout.write(open(H, encoding="utf-8").read())
    elif a.cmd == "ack": ack(a.by)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prompt history logger (RULES.md section C). Local only: history/ is git-ignored..

Files: history/prompts-<who>-YYYYMMWW.md  (YYYYMM = year+month of the week's Monday, WW = ISO week).

Subcommands:
  add        --who WHO --prompt TEXT|-  [--from NAME] [--summary TEXT] [--time "YYYY-MM-DD HH:MM"] [--model ID]
  summarize  --who WHO --summary TEXT   [--date YYYY-MM-DD] [--model ID]   fill the last '_pending_' summary
             (and correct its **Model:** line)
  show       [--date D | --since D] [--until D] [--who WHO|all]  print entries (prompt shortened)
  path       [--who WHO] [--date D]                              print the history file path
  exchange   --to AGENT --from SENDER --prompt TEXT|@file [--response TEXT|@file] [--time ...]
             [--model ID (model that produced the response)] [--from-model ID (sender's model)]
             log an agent communication in full: the recipient's file gets prompt + full response,
             the sender's file gets the prompt and a pointer (RULES.md C8). Senders: user, claude, codex, <agent-slug>.
  show       ... [--full]   print complete entries instead of shortened ones
  hook       Claude Code UserPromptSubmit hook: reads JSON on stdin, logs the prompt as user,
             prints a short rules reminder (added to the model context). Never fails the prompt.
  hook-agent Claude Code PostToolUse (Task|Agent|SendMessage) and SubagentStop hook: logs subagent
             prompts, full responses and agent-to-agent messages automatically. Never fails.
  backfill-model  insert '**Model:** not recorded' into entries written before the model rule.

Every entry carries a **Model:** line (RULES.md C9): the LLM name and version that produced the response
(for user prompts: the model that answered). Resolution order: --model, env PROMPT_LOG_MODEL, hook data,
Claude Code transcript, .claude/settings.json, else 'unknown'.
"""
import argparse, datetime as dt, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "history")


def _owner():
    """User name for file headers: env PROMPT_LOG_USER, else owner in config/profile.yaml, else 'user'."""
    if os.environ.get("PROMPT_LOG_USER"):
        return os.environ["PROMPT_LOG_USER"]
    try:
        m = re.search(r"(?m)^owner:\s*(.+?)\s*$", open(os.path.join(ROOT, "config", "profile.yaml"), encoding="utf-8").read())
        if m:
            return m.group(1).strip("\"'") or "user"
    except Exception:
        pass
    return "user"


USER_NAME = _owner()
SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{16,}|AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                    r"|\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b"      # IBAN
                    r"|\b(?:\d[ -]?){13,19}\b)")                                         # card-like digit runs
ENTRY = re.compile(r"(?m)^### (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) ([+-]\d{2}:\d{2})$")
REMINDER = ("RULES.md applies: check SCRIPTS.md before writing any script; check KNOWLEDGE.md before researching reference facts "
            "(platform formats, instrument identity, rules) and persist new findings in knowledge/; when the turn ends run: "
            "python3 scripts/prompt-log.py summarize --who user --summary '<max 2 lines>' --model '<your exact model id>' "
            "(every history entry must name the LLM and version, RULES C9)")
UNKNOWN_MODEL = "unknown"
NOT_RECORDED = "not recorded"

def _model_str(v):
    if isinstance(v, dict):
        v = v.get("id") or v.get("model") or v.get("display_name") or v.get("name")
    v = " ".join(str(v or "").split())
    return v if v and v != "<synthetic>" else ""

def model_from_transcript(path):
    """Model id of the last assistant message in a Claude Code transcript (JSONL). Best effort."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 400000))
            lines = fh.read().decode("utf-8", "replace").splitlines()
        for line in reversed(lines):
            try:
                o = json.loads(line)
            except Exception:
                continue
            m = _model_str((o.get("message") or {}).get("model")) if isinstance(o, dict) else ""
            if m:
                return m
    except Exception:
        pass
    return ""

def settings_model():
    for p in (os.path.join(ROOT, ".claude", "settings.json"), os.path.expanduser("~/.claude/settings.json")):
        try:
            m = _model_str(json.load(open(p, encoding="utf-8")).get("model"))
            if m:
                return m
        except Exception:
            pass
    return ""

def session_model(explicit=None, data=None):
    data = data or {}
    for cand in (explicit, os.environ.get("PROMPT_LOG_MODEL"), data.get("model"), data.get("model_id")):
        m = _model_str(cand)
        if m:
            return m
    for key in ("transcript_path", "agent_transcript_path"):
        if data.get(key):
            m = model_from_transcript(data[key])
            if m:
                return m
    return settings_model() or os.environ.get("ANTHROPIC_MODEL", "").strip() or UNKNOWN_MODEL

def agent_model(slug, data=None):
    """Model a Claude Code subagent runs on: its wrapper's frontmatter, else the session model."""
    try:
        txt = open(os.path.join(ROOT, ".claude", "agents", slug + ".md"), encoding="utf-8").read()
        m = re.search(r"(?m)^model:\s*(\S+)", txt.split("---")[1] if txt.startswith("---") else "")
        if m and m.group(1) not in ("inherit", "default"):
            return m.group(1)
    except Exception:
        pass
    if data and data.get("agent_transcript_path"):
        m = model_from_transcript(data["agent_transcript_path"])
        if m:
            return m
    return session_model(None, data)

def parse_time(s):
    if not s:
        return dt.datetime.now().astimezone()
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").astimezone()

def week_code(d):
    monday = (d - dt.timedelta(days=d.weekday())).date()
    return monday, d.isocalendar()[1], "%s%02d" % (monday.strftime("%Y%m"), d.isocalendar()[1])

def hist_path(who, d):
    monday, wk, code = week_code(d)
    return os.path.join(HIST, "prompts-%s-%s.md" % (who, code)), monday, wk

def tz(d):
    s = d.strftime("%z")
    return s[:3] + ":" + s[3:]

def ensure_header(path, who, d, monday, wk):
    if os.path.exists(path):
        return
    os.makedirs(HIST, exist_ok=True)
    who_line = "User: %s" % USER_NAME if who == "user" else "Agent: %s" % who
    open(path, "w", encoding="utf-8").write(
        "# %s\n\n- File: %s\n- Week: %02d (ISO), %s to %s\n- Created: %s %s\n- %s\n"
        % (os.path.basename(path), os.path.basename(path), wk, monday, monday + dt.timedelta(days=6),
           d.strftime("%Y-%m-%d %H:%M"), tz(d), who_line))

def fence_for(text):
    longest = max([len(m) for m in re.findall(r"`+", text)] + [2])
    return "`" * max(3, longest + 1)

def add(who, prompt, frm=None, summary=None, when=None, response=None, to=None, model=None):
    d = parse_time(when)
    path, monday, wk = hist_path(who, d)
    ensure_header(path, who, d, monday, wk)
    prompt = SECRET.sub("[REDACTED]", prompt.rstrip("\n"))
    f = fence_for(prompt)
    if response is not None:
        response = SECRET.sub("[REDACTED]", response.rstrip("\n"))
        if not summary:
            one = " ".join(response.split())
            summary = "Full response above. " + (one[:160] + ("…" if len(one) > 160 else ""))
    summary = " ".join((summary or "_pending_").split())
    entry = "\n### %s %s\n" % (d.strftime("%Y-%m-%d %H:%M"), tz(d))
    if frm:
        entry += "**From:** %s\n" % frm
    if to:
        entry += "**To:** %s\n" % to
    entry += "**Model:** %s\n" % (_model_str(model) or session_model())
    entry += "**Prompt:**\n%s\n%s\n%s\n" % (f, prompt, f)
    if response is not None:
        rf = fence_for(response)
        entry += "**Response:**\n%s\n%s\n%s\n" % (rf, response, rf)
    entry += "**Summary:** %s\n" % summary
    open(path, "a", encoding="utf-8").write(entry)
    return path

def summarize(who, summary, date=None, model=None):
    d = dt.datetime.strptime(date, "%Y-%m-%d").astimezone() if date else dt.datetime.now().astimezone()
    path, _, _ = hist_path(who, d)
    if not os.path.exists(path):
        sys.exit("no history file: %s" % path)
    text = open(path, encoding="utf-8").read()
    i = text.rfind("**Summary:** _pending_")
    if i < 0:
        sys.exit("no pending summary in %s" % os.path.basename(path))
    summary = " ".join(summary.split())
    if _model_str(model):
        j = text.rfind("**Model:** ", 0, i)
        k = text.find("\n", j) if j >= 0 else -1
        if j >= 0 and k >= 0:
            text = text[:j] + "**Model:** " + _model_str(model) + text[k:]
            i = text.rfind("**Summary:** _pending_")
    text = text[:i] + "**Summary:** " + summary + text[i + len("**Summary:** _pending_"):]
    open(path, "w", encoding="utf-8").write(text)
    print("updated", os.path.basename(path))

def slug(x, default="unknown"):
    x = re.sub(r"[^a-z0-9]+", "-", str(x or "").lower()).strip("-")
    return x or default

def read_arg(v):
    if v is None:
        return None
    if v.startswith("@") and os.path.isfile(v[1:]):
        return open(v[1:], encoding="utf-8").read()
    return v

def exchange(to, frm, prompt, response=None, when=None, model=None, from_model=None):
    to, frm = slug(to), slug(frm, "claude")
    p_to = add(to, prompt, frm=frm, response=response, when=when, model=model)
    p_from = None
    if frm != "user" and frm != to:
        one = " ".join((response or "(no response yet)").split())
        note = "Sent to %s; full response in %s. %s" % (to, os.path.basename(p_to), one[:160] + ("…" if len(one) > 160 else ""))
        p_from = add(frm, prompt, to=to, summary=note, when=when, model=from_model or model)
    return p_to, p_from

def text_of(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "\n".join(t for t in (text_of(i) for i in x) if t)
    if isinstance(x, dict):
        for k in ("text", "result", "content", "output", "message"):
            if k in x and x[k]:
                return text_of(x[k])
        return json.dumps(x, ensure_ascii=False)
    return str(x)

def seen_recently(who, response):
    """True if this response text is already in this week's file for the agent (dedupe PostToolUse vs SubagentStop)."""
    try:
        path = hist_path(who, dt.datetime.now().astimezone())[0]
        snippet = " ".join(response.split())[:120]
        return os.path.exists(path) and snippet and snippet in " ".join(open(path, encoding="utf-8").read().split())
    except Exception:
        return False

def hook_agent(data):
    ev = data.get("hook_event_name", "")
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    sender = data.get("agent_type") or "claude"
    if ev == "SubagentStop":
        who = slug(data.get("agent_type"), "subagent")
        resp = text_of(data.get("last_assistant_message"))
        if resp and not seen_recently(who, resp):
            add(who, "(prompt not captured by SubagentStop; see the orchestrator's PostToolUse entry)", frm="orchestrator", response=resp,
                model=agent_model(who, data))
        return
    if tool in ("Task", "Agent"):
        who = slug(ti.get("subagent_type") or ti.get("agent") or "general-purpose")
        prompt = text_of(ti.get("prompt")) or text_of(ti.get("description"))
        resp = text_of(data.get("tool_response"))
        exchange(who, sender, prompt, resp or "(response not captured)",
                 model=_model_str(ti.get("model")) or agent_model(who, data), from_model=session_model(None, data))
    elif tool == "SendMessage":
        to = slug(ti.get("to"))
        exchange(to, sender, text_of(ti.get("message") or ti.get("content") or ti.get("text")), None,
                 model=agent_model(to, data), from_model=session_model(None, data))

def show(who, date, since, until, full=False):
    lo = date or since
    hi = date or until
    pat = "prompts-*-*.md" if who == "all" else "prompts-%s-*.md" % who
    shown = 0
    for p in sorted(glob.glob(os.path.join(HIST, pat))):
        text = open(p, encoding="utf-8").read()
        parts = ENTRY.split(text)
        # parts: [header, date, time, tz, body, date, time, tz, body, ...]
        for k in range(1, len(parts), 4):
            day, hm, body = parts[k], parts[k + 1], parts[k + 3]
            if lo and day < lo:
                continue
            if hi and day > hi:
                continue
            if full:
                print("[%s] %s %s\n%s" % (os.path.basename(p)[8:-3].rsplit("-", 1)[0], day, hm, body.rstrip()))
                shown += 1
                continue
            m = re.search(r"\*\*Prompt:\*\*\n(`{3,})\n(.*?)\n\1\n", body, re.S)
            prompt = (m.group(2) if m else "").replace("\n", " ")
            s = re.search(r"\*\*Summary:\*\* (.*)", body)
            frm = re.search(r"\*\*From:\*\* (.*)", body)
            mdl = re.search(r"\*\*Model:\*\* (.*)", body)
            print("[%s] %s %s%s [%s]\n  prompt : %s\n  summary: %s" % (
                os.path.basename(p)[8:-3].rsplit("-", 1)[0], day, hm,
                " (from %s)" % frm.group(1) if frm else "",
                mdl.group(1) if mdl else NOT_RECORDED,
                prompt[:300] + ("…" if len(prompt) > 300 else ""), s.group(1) if s else ""))
            shown += 1
    if not shown:
        print("no entries")

def backfill_model():
    """Insert '**Model:** not recorded' before **Prompt:** in entries that lack a Model line."""
    changed = 0
    for p in sorted(glob.glob(os.path.join(HIST, "prompts-*-*.md"))):
        out, has_model, n = [], True, 0
        for line in open(p, encoding="utf-8").read().split("\n"):
            if line.startswith("### "):
                has_model = False
            elif line.startswith("**Model:**"):
                has_model = True
            elif line == "**Prompt:**" and not has_model:
                out.append("**Model:** " + NOT_RECORDED)
                has_model, n = True, n + 1
            out.append(line)
        if n:
            open(p, "w", encoding="utf-8").write("\n".join(out))
            changed += n
            print("%s: %d entries" % (os.path.basename(p), n))
    print("backfilled %d entries" % changed)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("--who", default="user"); a.add_argument("--prompt", required=True, help="text or - for stdin")
    a.add_argument("--from", dest="frm"); a.add_argument("--summary"); a.add_argument("--time"); a.add_argument("--model")
    s = sub.add_parser("summarize"); s.add_argument("--who", default="user"); s.add_argument("--summary", required=True); s.add_argument("--date"); s.add_argument("--model")
    x = sub.add_parser("exchange"); x.add_argument("--to", required=True); x.add_argument("--from", dest="frm", required=True)
    x.add_argument("--prompt", required=True, help="text or @file"); x.add_argument("--response", help="text or @file"); x.add_argument("--time")
    x.add_argument("--model", help="model that produced the response"); x.add_argument("--from-model", dest="from_model", help="sender's model")
    w = sub.add_parser("show"); w.add_argument("--who", default="all"); w.add_argument("--date"); w.add_argument("--since"); w.add_argument("--until"); w.add_argument("--full", action="store_true")
    p = sub.add_parser("path"); p.add_argument("--who", default="user"); p.add_argument("--date")
    sub.add_parser("hook")
    sub.add_parser("hook-agent")
    sub.add_parser("backfill-model")
    args = ap.parse_args()
    if args.cmd == "add":
        text = sys.stdin.read() if args.prompt == "-" else args.prompt
        print(add(args.who, text, args.frm, args.summary, args.time, model=args.model))
    elif args.cmd == "summarize":
        summarize(args.who, args.summary, args.date, args.model)
    elif args.cmd == "show":
        show(args.who, args.date, args.since, args.until, args.full)
    elif args.cmd == "exchange":
        a, b = exchange(args.to, args.frm, read_arg(args.prompt), read_arg(args.response), args.time,
                     args.model, args.from_model)
        print(a)
        if b:
            print(b)
    elif args.cmd == "backfill-model":
        backfill_model()
    elif args.cmd == "path":
        d = dt.datetime.strptime(args.date, "%Y-%m-%d").astimezone() if args.date else dt.datetime.now().astimezone()
        print(hist_path(args.who, d)[0])
    elif args.cmd == "hook":
        try:
            data = json.load(sys.stdin)
            prompt = data.get("prompt") or ""
            if prompt.strip():
                add("user", prompt, model=session_model(None, data))
            print(REMINDER)
        except Exception:
            pass
        sys.exit(0)
    elif args.cmd == "hook-agent":
        try:
            hook_agent(json.load(sys.stdin))
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()

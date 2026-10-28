#!/usr/bin/env python3
"""Find agent memory stored OUTSIDE the project and optionally import it (RULES.md section E).

usage: memory-audit.py [--import]
  Checks (HOME can be overridden with the HOME env var):
   1. Claude Code default auto memory: ~/.claude/projects/<encoded repo path>/memory (and *<repo name>*)
   2. Claude subagent memory: ~/.claude/agent-memory/ and <repo>/.claude/agent-memory/ (report only)
   3. In-repo config: .claude/settings.json autoMemoryDirectory = memory/claude
  --import  copy found Claude memory files into memory/claude/ (conflicts -> <name>.imported.md) and add index lines.
            Originals are NOT deleted.
exit code: 0 = nothing outside the project, 1 = outside memory found or config wrong.
Memory is local only: memory/ is git-ignored.
"""
import glob, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser(os.environ.get("HOME", "~"))
DO_IMPORT = "--import" in sys.argv
findings = []


def add_index(folder, line):
    p = os.path.join(ROOT, "memory", folder, "MEMORY.md")
    cur = open(p, encoding="utf-8").read() if os.path.exists(p) else "# Memory index\n\n"
    if line not in cur:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(cur.rstrip("\n") + "\n" + line + "\n")


enc = re.sub(r"[^A-Za-z0-9]", "-", ROOT)
cands = set(glob.glob(os.path.join(HOME, ".claude", "projects", enc, "memory")))
cands |= set(glob.glob(os.path.join(HOME, ".claude", "projects", "*" + os.path.basename(ROOT) + "*", "memory")))
for d in sorted(cands):
    files = glob.glob(os.path.join(d, "*.md"))
    if files:
        findings.append("Claude auto memory outside project: %s (%d files)" % (d, len(files)))
        if DO_IMPORT:
            dest = os.path.join(ROOT, "memory", "claude")
            os.makedirs(dest, exist_ok=True)
            for f in files:
                name = os.path.basename(f)
                target = os.path.join(dest, name)
                if name == "MEMORY.md":
                    for l in open(f, encoding="utf-8"):
                        if l.startswith("- "):
                            add_index("claude", l.rstrip("\n"))
                    continue
                if os.path.exists(target) and open(target, "rb").read() != open(f, "rb").read():
                    target = os.path.join(dest, name[:-3] + ".imported.md")
                shutil.copy(f, target)
            print("imported Claude memory from", d)

for d in (os.path.join(HOME, ".claude", "agent-memory"), os.path.join(ROOT, ".claude", "agent-memory")):
    if os.path.isdir(d) and os.listdir(d):
        findings.append("Claude subagent memory directory present: %s (do not set 'memory:' in agent frontmatter; move content into memory/ manually)" % d)

try:
    c = json.load(open(os.path.join(ROOT, ".claude", "settings.json")))
    if c.get("autoMemoryDirectory") != "memory/claude":
        findings.append(".claude/settings.json: autoMemoryDirectory is not 'memory/claude'")
except Exception as e:
    findings.append(".claude/settings.json unreadable: %s" % e)

if findings:
    print("\n".join("FOUND: " + f for f in findings))
    sys.exit(1)
print("memory-audit: OK - no memory outside the project")

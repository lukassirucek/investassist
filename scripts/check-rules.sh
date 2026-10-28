#!/usr/bin/env bash
# Verify RULES.md compliance: scripts documented, parsers listed, knowledge indexed, hooks wired, memory set up, history models present.
# usage: scripts/check-rules.sh        exit 0 = ok, 1 = findings (printed). Checks of local files (history, knowledge, memory) only run when they exist.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
fail=0; bad(){ echo "FAIL: $*"; fail=1; }
chk(){ # file registry
  local f b; for f in "$1"/*; do
    [[ -f $f ]] || continue; b=$(basename "$f"); case "$b" in README.md|__pycache__) continue;; esac
    grep -q "\`$b\`" "$2" 2>/dev/null || bad "$f not documented in $2"
    case "$b" in *.py) python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f" 2>/dev/null || bad "$f does not compile" ;; *.sh) bash -n "$f" || bad "$f syntax" ;; esac
  done; }
chk scripts SCRIPTS.md
chk parsers parsers/README.md
[[ -d local/scripts ]] && { [[ -f local/SCRIPTS.local.md ]] || bad "local/scripts exists but local/SCRIPTS.local.md is missing"; chk local/scripts local/SCRIPTS.local.md; }
if [[ -f KNOWLEDGE.md ]]; then
  for f in knowledge/*.md; do [[ -e $f ]] || continue; b=$(basename "$f"); [[ $b == README.md ]] && continue; grep -q "(knowledge/$b)" KNOWLEDGE.md || bad "knowledge/$b not in KNOWLEDGE.md"; done
  while read -r p; do [[ -z $p || -f $p ]] || bad "KNOWLEDGE.md links missing file $p"; done < <(grep -o '(knowledge/[^)]*\.md)' KNOWLEDGE.md | tr -d '()')
fi
grep -q '^@RULES.md' CLAUDE.md || bad "CLAUDE.md does not import RULES.md"
grep -q 'RULES.md' AGENTS.md || bad "AGENTS.md does not point to RULES.md"
for k in prompt-log.py hook-agent SubagentStop UserPromptSubmit memory-handover.py autoMemoryDirectory; do grep -q "$k" .claude/settings.json || bad ".claude/settings.json missing $k"; done
grep -q '^- C8 ' RULES.md || bad "RULES.md missing rule C8 (log all agent communications)"
grep -q '^## 0\. Every surface' RULES.md || bad "RULES.md missing section 0 (every surface, non-negotiable)"
grep -q '^- B6 ' RULES.md || bad "RULES.md missing rule B6 (save every opened source)"
grep -q 'Non-negotiable on every surface' CLAUDE.md || bad "CLAUDE.md missing the every-surface block"
grep -q 'summarize --who user --prompt' CLAUDE.md || bad "CLAUDE.md close-the-turn command lacks --prompt"
grep -q '^- C9 ' RULES.md || bad "RULES.md missing rule C9 (model on every history entry)"
for f in .gitignore; do for k in '/history/*' '/knowledge/*' '/memory/*' '/KNOWLEDGE.md'; do grep -qxF "$k" $f || bad ".gitignore missing $k"; done; done
if [[ -d memory/claude ]]; then
  for f in memory/claude/MEMORY.md memory/shared/MEMORY.md; do [[ -f $f ]] || bad "missing $f (run: python3 scripts/init_workspace.py)"; done
  python3 scripts/memory-audit.py >/dev/null 2>&1 || echo "WARN: memory-audit reports findings (run: python3 scripts/memory-audit.py)"
fi
for h in history/prompts-*.md; do [[ -f $h ]] || continue; n=$(grep -c '^### 20' "$h"); m=$(grep -c '^\*\*Model:\*\* ' "$h"); [[ $n -eq $m ]] || bad "$h: $((n-m)) entries without a **Model:** line (run prompt-log.py backfill-model, or add --model)"; done
grep -l '^\*\*Model:\*\* unknown' history/prompts-*.md >/dev/null 2>&1 && echo "WARN: some history entries have Model 'unknown' (correct with summarize --model)"
tracked=$(git ls-files history knowledge memory KNOWLEDGE.md 2>/dev/null | grep -v -e '^history/README.md$' -e '^knowledge/README.md$' -e '^memory/README.md$')
[[ -z $tracked ]] || bad "local-only files are tracked by git: $tracked"
[[ $fail -eq 0 ]] && echo "check-rules: OK"
exit $fail

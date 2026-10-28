#!/usr/bin/env python3
"""Create the private workspace in a fresh clone. Safe to rerun (never overwrites an existing file).

Usage: python3 scripts/init_workspace.py            # folders + config/*.yaml from the examples + data/reference/instruments.csv
       python3 scripts/init_workspace.py --demo     # also loads synthetic demo data and builds the demo dashboard (refuses if data/index already has files)
Also scaffolds the local working memory (RULES.md B, C, E): KNOWLEDGE.md, memory/*/MEMORY.md, history/, knowledge/.
Everything it creates is git-ignored (see .gitignore): config/*.yaml, data/, reports/, local/, CLAUDE.local.md, history/, knowledge/, memory/, KNOWLEDGE.md.
"""
import glob, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DIRS = ['data/inbox', 'data/raw', 'data/index', 'data/exposure', 'data/signals/raw', 'data/outlook/raw', 'data/ledger', 'data/fx', 'data/reference', 'data/reports', 'reports/alerts', 'local/parsers', 'local/scripts', 'history', 'knowledge', 'memory/claude', 'memory/codex', 'memory/shared', 'memory/handovers']


def run(*cmd):
    r = subprocess.run([sys.executable, '-I', *cmd])
    if r.returncode:
        sys.exit(f'step failed: {" ".join(cmd)}')


for d in DIRS:
    os.makedirs(d, exist_ok=True)
made = []
for ex in sorted(glob.glob('config/*.example.yaml')):
    dst = ex.replace('.example', '')
    if not os.path.exists(dst):
        shutil.copy(ex, dst); made.append(dst)
if not os.path.exists('data/reference/instruments.csv'):
    shutil.copy('examples/reference/instruments.example.csv', 'data/reference/instruments.csv'); made.append('data/reference/instruments.csv')
if not os.path.exists('CLAUDE.local.md'):
    open('CLAUDE.local.md', 'w', encoding='utf-8').write('# Personal rules (git-ignored)\nWritten by the `setup` skill: owner, tax wrappers, exclusions, language, anything the agent must always respect for this user.\n'); made.append('CLAUDE.local.md')
for src, dst in (('templates/workspace/KNOWLEDGE.md', 'KNOWLEDGE.md'), ('templates/workspace/MEMORY.md', 'memory/claude/MEMORY.md'),
                 ('templates/workspace/MEMORY.md', 'memory/codex/MEMORY.md'), ('templates/workspace/MEMORY.md', 'memory/shared/MEMORY.md')):
    if not os.path.exists(dst):
        shutil.copy(src, dst); made.append(dst)
if not os.path.exists('local/SCRIPTS.local.md'):
    open('local/SCRIPTS.local.md', 'w', encoding='utf-8').write('# Local scripts\n\nYour own scripts in local/scripts/ (RULES.md A2). One entry per script: purpose, usage, reads/writes, side effects.\n'); made.append('local/SCRIPTS.local.md')
print('created: ' + (', '.join(made) if made else 'nothing new'))

if '--demo' in sys.argv:
    if glob.glob('data/index/*.positions.csv'):
        sys.exit('data/index already has indexes: not loading the demo over real data.')
    import yaml
    p = yaml.safe_load(open('config/profile.yaml', encoding='utf-8')) or {}
    p.update(owner='Demo Investor', base_ccy='EUR', demo=True)
    yaml.safe_dump(p, open('config/profile.yaml', 'w', encoding='utf-8'), sort_keys=False)
    import datetime as dt, json, re
    today = dt.date.today()

    def rel(x):  # '+3d' / '-2d' -> ISO date relative to today; 'today' -> today
        if isinstance(x, str):
            if x == 'today':
                return today.isoformat()
            m = re.fullmatch(r'([+-]\d+)d', x)
            if m:
                return (today + dt.timedelta(days=int(m.group(1)))).isoformat()
            return x
        if isinstance(x, list):
            return [rel(i) for i in x]
        if isinstance(x, dict):
            return {k: rel(v) for k, v in x.items()}
        return x
    run('scripts/fx_set.py', 'USD=0.92', 'GBP=1.17')
    shutil.copy('examples/reference/instruments.example.csv', 'data/reference/instruments.csv')
    os.makedirs('data/raw/demo', exist_ok=True)
    txt = open('examples/demo/holdings_typed.csv', encoding='utf-8').read().replace(',today,', ',' + today.isoformat() + ',')
    open('data/raw/demo/holdings_typed.csv', 'w', encoding='utf-8').write(txt)
    run('scripts/manual_index.py', 'data/raw/demo/holdings_typed.csv', 'data/index')
    json.dump(rel(json.load(open('examples/demo/signals.json', encoding='utf-8'))), open('data/signals/raw/demo_scan.json', 'w', encoding='utf-8'), indent=1)
    run('scripts/build_master_index.py', 'data/index', 'data/fx/fx_latest.csv')
    run('scripts/build_exposure_map.py')
    run('scripts/signals.py', 'ingest', 'data/signals/raw/demo_scan.json')
    run('scripts/outlook.py', 'top')
    json.dump(rel(json.load(open('examples/demo/outlook_calls.json', encoding='utf-8'))), open('data/outlook/raw/demo_calls.json', 'w', encoding='utf-8'), indent=1)
    run('scripts/outlook.py', 'ingest', 'data/outlook/raw/demo_calls.json', today.isoformat())
    for off, src, kind, subj, summ, act, dl in ((-2, 'demo_broker', 'dividend', 'Demo: dividend paid', 'Synthetic demo mail.', 'none', ''),
                                                (-5, 'demo_lender', 'terms_change', 'Demo: lender changes its terms', 'Synthetic demo mail: terms change next week.', 'review', (today + dt.timedelta(days=6)).isoformat()),
                                                (-9, 'demo_bank', 'balance', 'Demo: monthly balance notice', 'Synthetic demo mail.', 'none', '')):
        cmd = ['scripts/mail_events.py', 'add', '--date', (today + dt.timedelta(days=off)).isoformat(), '--source', src, '--kind', kind, '--subject', subj, '--summary', summ, '--action', act]
        run(*(cmd + (['--deadline', dl] if dl else [])))
    run('scripts/pipeline.py', today.isoformat())
    print(f'DEMO ready: open data/reports/{today.isoformat()}/dashboard.html')
else:
    print('Next: open this folder in Claude Code (or Codex/ChatGPT agent) and run the `setup` skill, or read docs/getting-started.md.')

#!/usr/bin/env python3
"""Deterministic part of the daily run (no AI, no network): indexes -> master -> exposure -> watchlist -> digest -> outlook list -> dashboard.

Usage: python3 scripts/pipeline.py [YYYY-MM-DD] [--no-dashboard]
Each step is a separate script (`python3 -I scripts/<name>.py`); the first failing step stops the run and is named. News search, mail reading, the outlook calls and
publishing are done by the agent (skill `daily-scan`); this script is what it calls for the parts that need no judgement.
"""
import datetime as dt, os, subprocess, sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
day = args[0] if args else dt.date.today().isoformat()
HERE = os.path.dirname(os.path.abspath(__file__))
fx = 'data/fx/fx_latest.csv'
import glob
if not [f for f in glob.glob('data/index/*.positions.csv') if 'master' not in f]:
    sys.exit('No platform index in data/index/ yet. Run the `setup` skill (put exports in data/inbox/ first), or `python3 scripts/init_workspace.py --demo`.')
steps = [
    ('master index', ['build_master_index.py', 'data/index'] + ([fx] if os.path.exists(fx) else [])),
    ('exposure map', ['build_exposure_map.py']),
    ('watchlist', ['build_watchlist.py']),
    ('signals digest', ['signals.py', 'digest', day]),
    ('outlook shortlist', ['outlook.py', 'top']),
]
if '--no-dashboard' not in sys.argv:
    steps.append(('dashboard', ['build_dashboard_html.py', day]))
for name, cmd in steps:
    print(f'--- {name}')
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, cmd[0])] + cmd[1:])
    if r.returncode:
        sys.exit(f'FAILED at step "{name}" (exit {r.returncode}). Fix that step and rerun.')
print(f'OK. Dashboard: data/reports/{day}/dashboard.html')

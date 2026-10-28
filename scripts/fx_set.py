#!/usr/bin/env python3
"""Write data/fx/fx_latest.csv (units of the base currency per 1 unit of each currency). The agent looks the rates up with a cited, dated source.

Usage: python3 -I scripts/fx_set.py [--date YYYY-MM-DD] USD=21.83 EUR=24.33 GBP=29.05
The base currency itself (config/profile.yaml) is added with rate 1. Existing rows for other currencies are kept; given ones are replaced.
"""
import csv, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BASE

P = 'data/fx/fx_latest.csv'
args = sys.argv[1:]
day = dt.date.today().isoformat()
if '--date' in args:
    i = args.index('--date'); day = args[i + 1]; del args[i:i + 2]
if not args:
    print(__doc__); sys.exit(1)
cur = {r['ccy']: (r['to_base'], r['date']) for r in csv.DictReader(open(P, encoding='utf-8'))} if os.path.exists(P) else {}
cur[BASE] = ('1', day)
for a in args:
    k, v = a.split('=')
    cur[k.upper()] = (str(float(v)), day)
os.makedirs(os.path.dirname(P), exist_ok=True)
with open(P, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['ccy', 'to_base', 'date'])
    for k in sorted(cur): w.writerow([k, *cur[k]])
print(f'{P}: ' + ', '.join(f'{k} {v[0]} ({v[1]})' for k, v in sorted(cur.items())))

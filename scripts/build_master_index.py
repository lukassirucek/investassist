#!/usr/bin/env python3
"""Concatenate data/index/*.positions.csv into master.positions.csv + master.index.md.
Usage: python3 -I scripts/build_master_index.py [index_dir=data/index] [fx_csv]
fx_csv (optional): columns ccy,to_base,date (units of the base currency per 1 unit of ccy; legacy header to_czk accepted)
  -> adds cost_base / value_base in the profile's base currency (missing FX => blank, listed in md).
"""
import csv, glob, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER, BASE
from collections import defaultdict

def fnum(x):
    try: return float(x)
    except Exception: return None

def main(idx='data/index', fx_path=None):
    files = sorted(f for f in glob.glob(os.path.join(idx, '*.positions.csv')) if not os.path.basename(f).startswith('master'))
    fx = {}
    if fx_path:
        for r in csv.DictReader(open(fx_path, encoding='utf-8')):
            fx[r['ccy']] = (float(r.get('to_base') or r['to_czk']), r.get('date', ''))
    rows, cols = [], []
    for f in files:
        rd = csv.DictReader(open(f, encoding='utf-8'))
        for c in rd.fieldnames:
            if c not in cols: cols.append(c)
        rows += list(rd)
    if 'owner' not in cols: cols.append('owner')
    for r in rows: r['owner'] = r.get('owner') or OWNER
    extra = ['cost_base', 'value_base']
    nofx = set()
    for r in rows:
        ccy = r.get('report_ccy', '')
        rate = (1.0 if ccy == BASE else fx.get(ccy, (None,))[0])
        for src, dst in (('cost', 'cost_base'), ('value', 'value_base')):
            v = fnum(r.get(src))
            r[dst] = f'{v * rate:.2f}' if (v is not None and rate) else ''
            if v is not None and not rate: nofx.add(ccy)
    out_cols = cols + extra
    with open(os.path.join(idx, 'master.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=out_cols); w.writeheader(); w.writerows(rows)
    by = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
    for r in rows:
        if r.get('status') in ('sold_out', 'converted', 'repaid'): continue
        k = (r['owner'], r['platform'], r['asset_class'], r['report_ccy'])
        cnt[k] += 1; by[k]['cost'] += fnum(r['cost']) or 0; by[k]['value'] += fnum(r['value']) or 0
    md = [f"# Master index\n\ngenerated: {dt.date.today()} | platforms: {', '.join(sorted({r['platform'] for r in rows})) or 'none'} | rows: {len(rows)}\n\n",
          "| owner | platform | asset class | ccy | positions held | cost | value (where known) |\n|---|---|---|---|---:|---:|---:|\n"]
    for k in sorted(by):
        md.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {cnt[k]} | {by[k]['cost']:,.2f} | {by[k]['value']:,.2f} |\n")
    if nofx:
        md.append(f"\nNo FX provided for: {', '.join(sorted(nofx))} - {BASE} totals not computed. Provide a dated fx csv (ccy,to_base,date).\n")
    md.append("\nFormat of the per-platform indexes: docs/index-spec.md.\n")
    open(os.path.join(idx, 'master.index.md'), 'w', encoding='utf-8').write(''.join(md))
    print(f'{len(rows)} rows from {len(files)} indexes')

if __name__ == '__main__':
    main(*sys.argv[1:3])

#!/usr/bin/env python3
"""Valuation marks: bring a platform's index to a newer TOTAL shown by its app when no position-level data exists
(e.g. Portu or Indigo: positions come from a monthly/quarterly statement, the app screenshot shows only a newer total).

Usage: python3 -I scripts/marks_index.py <marks.csv> [index_dir=data/index] [fx_csv=data/fx/fx_latest.csv]
Input columns: platform, owner, app_total, ccy, valuation_date, source, notes
  owner: blank or the profile owner = own positions of that platform; any other name = that owner's rows only (the mark then carries that owner).
Output: data/index/marks.positions.csv + marks.index.md. One row per input line: mark = app_total - sum(value of the platform's rows for that owner, status not sold_out/converted/repaid,
excluding earlier marks). Row values are converted from their own `report_ccy` to the mark's ccy with the fx csv (rows in several currencies, e.g. Patria CZK/USD/GBP, would otherwise be summed raw). asset_class `other`, confidence medium, notes say INFERENCE. The platform's own index (positions from the statement) is NOT changed: exposure by instrument stays
as of the statement; only the platform total follows the app. Re-run after each statement rebuild (the mark is recomputed against the new statement total, so stale marks cannot add up).
"""
import csv, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER
COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner']

def load_fx(fx_path):
    fx = {'CZK': 1.0}
    if fx_path and os.path.exists(fx_path):
        for r in csv.DictReader(open(fx_path, encoding='utf-8')):
            fx[r['ccy']] = float(r.get('to_base') or r['to_czk'])
    return fx

def main(path, idx='data/index', fx_path='data/fx/fx_latest.csv'):
    fx = load_fx(fx_path)
    out, lines = [], []
    for m in csv.DictReader(open(path, encoding='utf-8-sig')):
        plat, owner = m['platform'].strip(), (m.get('owner') or '').strip()
        own = owner in ('', OWNER)
        pf = os.path.join(idx, plat + '.positions.csv')
        base = 0.0
        total, ccy = float(m['app_total']), m['ccy'].strip()
        for r in csv.DictReader(open(pf, encoding='utf-8')):
            if r.get('status') in ('sold_out', 'converted', 'repaid'): continue
            ro = (r.get('owner') or '').strip()
            if (own and ro in ('', OWNER)) or (not own and ro == owner):
                rc = (r.get('report_ccy') or ccy).strip()
                if rc != ccy and (rc not in fx or ccy not in fx):
                    sys.exit(f'No FX for {rc}->{ccy} in {fx_path}: cannot compute the mark for {plat}')
                base += float(r.get('value') or 0) * (1.0 if rc == ccy else fx[rc] / fx[ccy])
        mark = total - base
        out.append(dict(platform=plat, account='Valuation mark since statement', portfolio_type='', asset_class='other', instrument_id=f'MARK_{plat.upper()}', name=f'Valuation mark ({plat}: app total - statement total)',
                        status='held', native_ccy=ccy, report_ccy=ccy, value=f'{mark:.2f}', valuation_date=m['valuation_date'], confidence='medium', owner=owner if not own else '',
                        notes=f"INFERENCE: app total {total:,.2f} ({m.get('source','')}) minus statement-based rows {base:,.2f}; includes market moves, fees, flows and unsettled trades since the statement. {m.get('notes','')}".strip()))
        lines.append((plat, owner or OWNER, base, total, mark, ccy, m['valuation_date'], m.get('source', '')))
    with open(os.path.join(idx, 'marks.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(out)
    md = f"---\nplatform: marks\nsource_type: valuation marks from app totals ({os.path.basename(path)})\nvaluation_date: {max(l[6] for l in lines)}\ngenerated: {dt.date.today().isoformat()}\npositions_csv: marks.positions.csv\n---\n# Valuation marks\n\nOne row per platform where only a newer TOTAL is known. The platform's own index keeps the statement positions.\n\n| Platform | Owner | Statement-based total | App total | Mark | Ccy | As of | Source |\n|---|---|---:|---:|---:|---|---|---|\n"
    md += ''.join(f"| {a} | {b} | {c:,.2f} | {d:,.2f} | {e:+,.2f} | {f} | {g} | {h} |\n" for a, b, c, d, e, f, g, h in lines)
    md += f"\n- Rebuild: `python3 -I scripts/marks_index.py {path} {idx}`\n"
    open(os.path.join(idx, 'marks.index.md'), 'w', encoding='utf-8').write(md)
    for l in lines: print(f'mark {l[0]} ({l[1]}): statement {l[2]:,.2f} -> app {l[3]:,.2f} = {l[4]:+,.2f} {l[5]}')

if __name__ == '__main__':
    main(*sys.argv[1:4])

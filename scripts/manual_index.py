#!/usr/bin/env python3
"""Typed / transcribed holdings -> per-platform index (data/index/<platform>.positions.csv + .index.md).

Usage: python3 -I scripts/manual_index.py <input.csv> [out_dir=data/index]

Use it for anything without a machine-readable export: a typed list, a transcribed screenshot, a P2P/loan platform overview.
Input CSV columns (header required; blank = unknown, never estimate):
  platform, account, portfolio_type, asset_class, instrument_id, symbol, name, country, units, price, cost, value, ccy, valuation_date, owner, status, confidence, notes, interest_rate_pct, pnl, maturity_date, risk_rating
  - pnl (optional): gain/loss shown by the app; when `cost` is blank and value + pnl are given, cost = value - pnl (marked INFERENCE in notes)
  - maturity_date, risk_rating (optional): for loans / crowdlending projects
  - one row per position; several platforms may share one file (one index per platform is written)
  - asset_class: stock | etf | fund | bond | crypto | cash | gold | p2p_loan | crowdlend_project | real_estate | commodity | loan_liability | other
  - portfolio_type: tax wrapper if the platform has several (e.g. regular / retirement / ISA); blank otherwise
  - value = market value in `ccy` at `valuation_date`; if blank and units+price are given, value = units x price (marked in notes)
  - status: held (default) | sold_out | late | default | repaid
  - row with asset_class `total` = the total the platform shows; it is used only to reconcile and is not a position
Output follows docs/index-spec.md. Idempotent: the same input gives the same output (a new input for a platform replaces its index).
"""
import csv, datetime as dt, os, sys
from collections import defaultdict

COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct', 'maturity_date', 'risk_rating']


def num(x):
    x = (x or '').strip().replace(' ', '').replace(' ', '')
    if not x:
        return None
    if ',' in x and '.' not in x:
        x = x.replace(',', '.')
    return float(x.replace(',', ''))


def main(path, out='data/index'):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    by = defaultdict(list)
    for r in rows:
        if not (r.get('platform') or '').strip():
            raise SystemExit('every row needs a platform')
        by[r['platform'].strip()].append(r)
    os.makedirs(out, exist_ok=True)
    for plat, rs in by.items():
        pos, totals, warn = [], {}, []
        for r in rs:
            ccy = (r.get('ccy') or '').strip().upper()
            v, u, p, c = num(r.get('value')), num(r.get('units')), num(r.get('price')), num(r.get('cost'))
            note = (r.get('notes') or '').strip()
            if (r.get('asset_class') or '').strip() == 'total':
                if v is not None:
                    totals[(r.get('portfolio_type') or '').strip() or 'all'] = v
                continue
            if v is None and u is not None and p is not None:
                v = u * p
                note = (note + '; ' if note else '') + 'value = units x price (derived)'
            pnl = num(r.get('pnl'))
            if c is None and v is not None and pnl is not None:
                c = v - pnl
                note = (note + '; ' if note else '') + 'cost = value - app gain/loss (INFERENCE)'
            if not ccy:
                warn.append(f"{r.get('name') or r.get('instrument_id')}: no currency, row skipped"); continue
            pos.append(dict(platform=plat, account=(r.get('account') or '').strip(), portfolio_type=(r.get('portfolio_type') or '').strip(), asset_class=(r.get('asset_class') or 'other').strip(),
                            instrument_id=(r.get('instrument_id') or r.get('symbol') or r.get('name') or '').strip(), symbol=(r.get('symbol') or '').strip(), name=(r.get('name') or '').strip(),
                            country=(r.get('country') or '').strip(), status=(r.get('status') or 'held').strip(), native_ccy=ccy, units_net='' if u is None else f'{u:g}', report_ccy=ccy,
                            cost='' if c is None else f'{c:.2f}', value='' if v is None else f'{v:.2f}', price='' if p is None else f'{p:g}', price_ccy=ccy if p is not None else '',
                            valuation_date=(r.get('valuation_date') or '').strip(), confidence=(r.get('confidence') or 'medium').strip(), notes=note,
                            owner=(r.get('owner') or '').strip(), interest_rate_pct=(r.get('interest_rate_pct') or '').strip(),
                            maturity_date=(r.get('maturity_date') or '').strip(), risk_rating=(r.get('risk_rating') or '').strip()))
        with open(os.path.join(out, f'{plat}.positions.csv'), 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore'); w.writeheader(); w.writerows(pos)
        sums = defaultdict(float)
        for r in pos:
            if r['value'] and r['status'] not in ('sold_out', 'repaid'):
                sums[(r['report_ccy'], r['portfolio_type'] or 'all')] += float(r['value'])
        dates = sorted({r['valuation_date'] for r in pos if r['valuation_date']})
        vd = dates[-1] if dates else ''
        md = [f'---\nplatform: {plat}\nsource_type: typed or transcribed ({os.path.basename(path)})\nvaluation_date: {vd}\ngenerated: {dt.date.today().isoformat()}\npositions_csv: {plat}.positions.csv\n---\n',
              f'# {plat} index\n\n| ccy | portfolio type | positions value |\n|---|---|---:|\n']
        for (ccy, pt), s in sorted(sums.items()):
            md.append(f'| {ccy} | {pt} | {s:,.2f} |\n')
        if totals:
            md.append('\n## Reconciliation vs the total the platform shows\n| portfolio type | stated total | sum of positions | gap |\n|---|---:|---:|---:|\n')
            for pt, t in totals.items():
                s = sum(v for (ccy, k), v in sums.items() if pt in ('all', k))
                md.append(f'| {pt} | {t:,.2f} | {s:,.2f} | {t - s:,.2f} |\n')
        md.append('\n## Caveats\n- Typed or transcribed data: confidence is medium unless a statement says otherwise. Unknown values stay blank.\n')
        for w_ in warn:
            md.append(f'- WARNING {w_}\n')
        open(os.path.join(out, f'{plat}.index.md'), 'w', encoding='utf-8').write(''.join(md))
        print(f'OK {plat}: {len(pos)} positions' + (f', {len(warn)} warnings' if warn else ''))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(*sys.argv[1:3])

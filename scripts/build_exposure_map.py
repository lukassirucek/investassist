#!/usr/bin/env python3
"""Join data/index/master.positions.csv with data/reference/instruments.csv and a dated FX table -> exposure tables in the base currency (config/profile.yaml).
Usage: python3 -I scripts/build_exposure_map.py [master=data/index/master.positions.csv] [fx=data/fx/fx_latest.csv] [ref=data/reference/instruments.csv] [out=data/exposure]
Outputs: holdings_enriched.csv, exposure_<dim>.csv, exposure_map.md, unmapped.csv. Owner = profile owner = own portfolio; other owners (e.g. a child's account) are reported separately and excluded from own totals.
Rules: values are base-currency amounts at the FX table rates; a crypto row without a value is priced from the same coin on another platform (INFERENCE); materials/themes overlap (a holding counts fully under each tag).
"""
import csv, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER, BASE
from collections import defaultdict

SP500_MIX = {'Information Technology': 33.5, 'Financials': 13, 'Communication Services': 10, 'Consumer Discretionary': 10.5, 'Health Care': 9.5, 'Industrials': 8.5,
             'Consumer Staples': 5, 'Energy': 3, 'Utilities': 2.5, 'Real Estate': 2, 'Materials': 2}  # approximate index weights (INFERENCE, refresh from provider factsheet)
NASDAQ_MIX = {'Information Technology': 50, 'Communication Services': 16, 'Consumer Discretionary': 13, 'Health Care': 5, 'Consumer Staples': 5, 'Industrials': 5, 'Other': 6}
MIXES = {'S&P 500': SP500_MIX, 'S&P 500 (EUR hedged)': SP500_MIX, 'Nasdaq-100': NASDAQ_MIX}
HELD = ('held', 'held_unverified', 'late', 'default')

def f(x):
    try: return float(x)
    except Exception: return None

def load_ref(p):
    ref = {}
    for r in csv.DictReader(open(p, encoding='utf-8')):
        for k in r['ids'].split('|'):
            ref[k.strip().lower()] = r
    return ref

def lookup(ref, row):
    # reference keys tried in order: platform:<platform>:<asset_class>, then ISIN/symbol/name; cash falls back to cash:<ccy> or cash
    k0 = f"platform:{row['platform']}:{row['asset_class']}".lower()
    if k0 in ref: return ref[k0]
    if row['asset_class'] == 'cash':
        return ref.get(row['instrument_id'].lower()) or ref.get('cash:' + row['report_ccy'].lower()) or ref.get('cash')
    for k in (row['instrument_id'], row['symbol'], row['name']):
        if k and k.lower() in ref: return ref[k.lower()]
    for k, v in ref.items():
        if len(k) > 6 and row['instrument_id'].lower().startswith(k): return v
    return None

def main(master='data/index/master.positions.csv', fxp='data/fx/fx_latest.csv', refp='data/reference/instruments.csv', out='data/exposure'):
    fx = {r['ccy']: float(r.get('to_base') or r['to_czk']) for r in csv.DictReader(open(fxp, encoding='utf-8'))} if os.path.exists(fxp) else {}
    fx.setdefault(BASE, 1.0)
    fxdate = {r['ccy']: r['date'] for r in csv.DictReader(open(fxp, encoding='utf-8'))} if os.path.exists(fxp) else {}
    fxdate.setdefault(BASE, '')
    ref = load_ref(refp)
    rows = [r for r in csv.DictReader(open(master, encoding='utf-8')) if r['status'] in HELD]
    # coin prices (value per unit, in that row's report currency) from any platform that shows both value and units
    coin = {}
    for r in rows:
        if r['asset_class'] == 'crypto' and f(r['value']) and f(r['units_net']) and r['symbol'] not in coin:
            coin[r['symbol']] = (f(r['value']) / f(r['units_net']), r['report_ccy'])
    enriched, unmapped = [], []
    for r in rows:
        v, rate, note = f(r['value']), fx.get(r['report_ccy']), ''
        if v is None and r['asset_class'] == 'crypto' and r['symbol'] in coin and f(r['units_net']):
            v, rate, note = f(r['units_net']) * coin[r['symbol']][0], fx.get(coin[r['symbol']][1]), 'priced from the same coin on another platform (INFERENCE)'
        if v is None or rate is None:
            unmapped.append(dict(r, reason='no value or no fx')); continue
        m = lookup(ref, r)
        if not m:
            unmapped.append(dict(r, reason='no reference match')); continue
        cost = f(r['cost']); crate = fx.get(r['report_ccy']) or 0
        e = dict(platform=r['platform'], owner=r.get('owner') or OWNER, account=r['account'], portfolio_type=r['portfolio_type'] or 'n/a', instrument=m['name'], ref_ids=m['ids'].split('|')[0],
                 cls=m['class'], sector=m['sector'], industry=m['industry'], sub_industry=m['sub_industry'], hq=m['hq'] or 'n/a (fund/other)', revenue_regions=m['revenue_regions'] or 'n/a',
                 raw_materials=m['raw_materials'], themes=m['themes'], ccy=r['report_ccy'], value_base=round(v * rate, 2), cost_base=round(cost * crate, 2) if cost is not None and r['asset_class'] != 'cash' else '',
                 note=note)
        enriched.append(e)
    os.makedirs(out, exist_ok=True)
    cols = list(enriched[0].keys())
    with open(os.path.join(out, 'holdings_enriched.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(enriched)
    with open(os.path.join(out, 'unmapped.csv'), 'w', newline='', encoding='utf-8') as fh:
        if unmapped:
            w = csv.DictWriter(fh, fieldnames=list(unmapped[0].keys())); w.writeheader(); w.writerows(unmapped)
    own = [e for e in enriched if e['owner'] == OWNER]
    kids = [e for e in enriched if e['owner'] != OWNER]
    tot = sum(e['value_base'] for e in own)

    def agg(items, keyf, split=False):
        d = defaultdict(float)
        for e in items:
            ks = keyf(e)
            for k in (ks if split else [ks]): d[k.strip() or 'n/a'] += e['value_base']
        return sorted(d.items(), key=lambda kv: -kv[1])

    def sector_lt(e):
        mix = MIXES.get(e['sub_industry'])
        return list(mix.items()) if (mix and e['cls'] in ('equity_etf', 'fund')) else [(e['sector'] if e['cls'] not in ('equity_etf', 'fund') else 'Diversified/other ETF', 100)]
    dims = {
        'platform': lambda e: e['platform'], 'portfolio_type': lambda e: e['portfolio_type'], 'class': lambda e: e['cls'], 'sector': lambda e: e['sector'], 'industry': lambda e: e['industry'],
        'hq_country': lambda e: e['hq'], 'currency': lambda e: e['ccy'], 'instrument': lambda e: e['instrument'], 'sub_industry': lambda e: e['sub_industry']}
    tables = {}
    for n, kf in dims.items(): tables[n] = agg(own, kf)
    tables['revenue_region'] = agg(own, lambda e: [x for x in e['revenue_regions'].split(';') if x] or ['n/a'], True)
    tables['raw_material_touching'] = agg(own, lambda e: [x for x in e['raw_materials'].split(';') if x] or ['none'], True)
    tables['theme_touching'] = agg(own, lambda e: [x for x in e['themes'].split(';') if x] or ['none'], True)
    sl = defaultdict(float)
    for e in own:
        for k, wgt in sector_lt(e):
            tw = sum(x[1] for x in sector_lt(e))
            sl[k] += e['value_base'] * wgt / tw
    tables['sector_lookthrough_approx'] = sorted(sl.items(), key=lambda kv: -kv[1])
    for n, t in tables.items():
        with open(os.path.join(out, f'exposure_{n}.csv'), 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh); w.writerow([n, 'value_base', 'pct_of_own']); [w.writerow([k, round(v, 2), round(v / tot * 100, 2)]) for k, v in t]
    # md
    def tbl(t, n=12):
        return f'| item | {BASE} | % |\n|---|---:|---:|\n' + ''.join(f'| {k} | {v:,.0f} | {v/tot*100:.1f} |\n' for k, v in t[:n])
    top = tables['instrument'][:10]
    hhi = sum((v / tot * 100) ** 2 for _, v in tables['instrument'])
    md = f"# Exposure map\n\ngenerated: {dt.date.today()} | own portfolio total: **{tot:,.0f} {BASE}** ({len(own)} rows) | other owners (excluded): {sum(e['value_base'] for e in kids):,.0f} {BASE} | unmapped rows: {len(unmapped)}\nFX: " + ', '.join(f'{c} {fx[c]} ({fxdate[c]})' for c in fx if c != BASE) + "\n\n"
    for title, n, k in (('By platform', 'platform', 20), ('By asset class', 'class', 20), ('By portfolio type', 'portfolio_type', 5), ('Top instruments (aggregated across platforms)', 'instrument', 15),
                        ('By sector (single names + non-ETF)', 'sector', 15), ('Sector look-through (approximate, S&P 500/Nasdaq weights are INFERENCE)', 'sector_lookthrough_approx', 15), ('By HQ country', 'hq_country', 15),
                        ('By revenue region (holdings touching region; overlapping)', 'revenue_region', 15), ('Currency of holding', 'currency', 6),
                        ('Raw materials touched (overlapping, indicative)', 'raw_material_touching', 20), ('Themes touched (overlapping)', 'theme_touching', 20)):
        md += f'## {title}\n' + tbl(tables[n], k) + '\n'
    md += f"Concentration: top-10 instruments = {sum(v for _, v in top)/tot*100:.1f} % of own total; HHI {hhi:,.0f}.\n"
    if kids:
        md += '\n## Other owners (not in own totals)\n' + '\n'.join(f"- {o}: {sum(e['value_base'] for e in kids if e['owner']==o):,.0f} {BASE}" for o in sorted({e['owner'] for e in kids})) + '\n'
    open(os.path.join(out, 'exposure_map.md'), 'w', encoding='utf-8').write(md)
    print(f'own total {tot:,.0f} {BASE}; rows {len(own)}; kids {sum(e["value_base"] for e in kids):,.0f}; unmapped {len(unmapped)}')
    for u in unmapped: print('UNMAPPED', u['platform'], u['instrument_id'][:30], u['name'][:30], u['reason'])

if __name__ == '__main__':
    a = sys.argv[1:]
    main(*a[:4])

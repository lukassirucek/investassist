#!/usr/bin/env python3
"""Generate config/watchlist.generated.yaml + data/exposure/watchlist_queries.csv from data/exposure/holdings_enriched.csv (own portfolio only).
Tiers by weight of the entity in the own portfolio: T1 >= 1 % (daily), T2 0.2-1 % (daily, short), T3 < 0.2 % (weekly batch). Manual items stay in config/watchlist.yaml.
Usage: python3 -I scripts/build_watchlist.py [holdings=data/exposure/holdings_enriched.csv] [out_yaml=config/watchlist.generated.yaml] [out_csv=data/exposure/watchlist_queries.csv]
"""
import csv, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER, BASE
from collections import defaultdict

REGION_QUERIES = {
    'US': ['United States tariffs trade policy markets', 'US Federal Reserve rates decision'],
    'China': ['China export controls sanctions', 'China economy stimulus'],
    'Taiwan': ['Taiwan Strait tension semiconductor supply'],
    'Middle East': ['Middle East conflict oil supply Hormuz', 'Red Sea shipping disruption'],
    'Russia-Ukraine': ['Russia Ukraine war sanctions ammunition gas', 'EU sanctions package Russia'],
    'Chile': ['Chile copper lithium policy mining'], 'Brazil': ['Brazil economy real central bank'], 'UK': ['UK economy Bank of England'],
    'Eurozone': ['ECB rates euro area banks'], 'EU': ['EU regulation energy prices'], 'Japan': ['Japan yen Bank of Japan'], 'EM': ['emerging markets dollar strength'],
}
COMMODITY_QUERIES = {'gold': 'gold price outlook central banks', 'silver': 'silver price outlook', 'copper': 'copper price supply', 'aluminium': 'aluminium price supply energy',
    'steel': 'steel prices Europe', 'crude oil': 'Brent crude oil price outlook OPEC', 'natural gas': 'TTF natural gas price Europe storage', 'uranium': 'uranium price supply enrichment',
    'lithium': 'lithium price outlook', 'coal': 'coal price Europe', 'CO2 allowances': 'EU carbon price EUA', 'electricity': 'European power prices', 'bitcoin': 'bitcoin price ETF flows',
    'semiconductors': 'semiconductor supply AI chip demand export controls', 'sugar': 'sugar price outlook', 'coffee': 'coffee price', 'wheat': 'wheat price', 'cooking oil': 'vegetable oil prices',
    'jet fuel (oil)': 'jet fuel price airlines', 'aluminium cans': 'aluminium price', 'rare earths': 'rare earths export China', 'titanium': 'titanium supply aerospace',
    'nickel': 'nickel price supply', 'gallium': 'gallium germanium export controls', 'helium': 'helium shortage semiconductors', 'lithium brine': 'lithium price outlook'}
THEME_QUERIES = {'bitcoin': 'bitcoin regulation news', 'AI': 'AI capex data center spending', 'defense': 'NATO defence spending contracts', 'nuclear': 'nuclear power SMR policy',
    'real estate': 'real estate developers loans defaults', 'consumer credit': 'consumer loans delinquency', 'EU banks': 'euro area bank profits rates',
    'small cap': 'small cap stocks outlook', 'rates': 'bond yields inflation expectations', 'credit': 'credit spreads high yield', 'gold': 'gold ETF flows', 'crypto': 'crypto market news altcoins'}

def tier(p): return 'T1' if p >= 1 else 'T2' if p >= 0.2 else 'T3'

def main(hp='data/exposure/holdings_enriched.csv', oy='config/watchlist.generated.yaml', oc='data/exposure/watchlist_queries.csv'):
    E = [e for e in csv.DictReader(open(hp, encoding='utf-8')) if e['owner'] == OWNER]
    tot = sum(float(e['value_base']) for e in E)
    inst, comm, reg, theme = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    meta = {}
    for e in E:
        v = float(e['value_base']); inst[e['instrument']] += v; meta[e['instrument']] = e
        for k in e['raw_materials'].split(';'):
            if k.strip() and k != 'diversified': comm[k.strip()] += v
        for k in set([x for x in e['revenue_regions'].split(';') if x] + ([e['hq']] if len(e['hq']) == 2 else [])): reg[k.strip()] += v
        for k in e['themes'].split(';'):
            if k.strip(): theme[k.strip()] += v
    Q = []
    for n, v in sorted(inst.items(), key=lambda kv: -kv[1]):
        e = meta[n]
        if e['cls'] in ('cash',): continue
        p = v / tot * 100; t = tier(p)
        if e['cls'] in ('equity_single', 'crypto'):
            Q.append((t, 'company', n, p, f'{n} stock news'))
            if t in ('T1', 'T2'): Q.append((t, 'company', n, p, f'{n} earnings guidance outlook'))
        elif e['cls'] in ('equity_etf', 'bond_etf', 'fund', 'cert'):
            Q.append((t, 'fund', n, p, f'{e["sub_industry"]} market outlook'))
    for k, v in sorted(comm.items(), key=lambda kv: -kv[1]):
        p = v / tot * 100
        Q.append((tier(p), 'commodity', k, p, COMMODITY_QUERIES.get(k, f'{k} price supply news')))
    reg_map = {'Taiwan': sum(v for k, v in comm.items() if k in ('semiconductors', 'silicon wafers')), 'Middle East': comm.get('crude oil', 0) + comm.get('jet fuel (oil)', 0), 'Russia-Ukraine': theme.get('defense', 0) + comm.get('natural gas', 0) + comm.get('coal', 0)}
    for k, v in sorted(reg.items(), key=lambda kv: -kv[1]):
        for q in REGION_QUERIES.get(k) or ([f'{k} economy central bank interest rates', f'{k} property prices mortgage rates'] if len(k) == 2 and k.isupper() else []):
            Q.append((tier(v / tot * 100), 'region', k, v / tot * 100, q))
    for k, v in reg_map.items():
        for q in REGION_QUERIES[k]: Q.append((tier(v / tot * 100) if v else 'T3', 'region', k, v / tot * 100, q))
    for k, v in sorted(theme.items(), key=lambda kv: -kv[1]):
        if k in THEME_QUERIES: Q.append((tier(v / tot * 100), 'theme', k, v / tot * 100, THEME_QUERIES[k]))
    seen, U = set(), []
    for q in Q:
        if q[4] not in seen: seen.add(q[4]); U.append(q)
    with open(oc, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['tier', 'type', 'entity', 'weight_pct', 'query'])
        for t, ty, en, p, q in sorted(U, key=lambda x: (x[0], -x[3])): w.writerow([t, ty, en, round(p, 2), q])
    with open(oy, 'w', encoding='utf-8') as fh:
        fh.write(f'# GENERATED {dt.date.today()} by scripts/build_watchlist.py from own portfolio {tot:,.0f} {BASE}. Do not edit; put manual items in config/watchlist.yaml.\n')
        fh.write('tiers: {T1: "weight >= 1 % - search daily, full depth", T2: "0.2-1 % - search daily, headline depth", T3: "< 0.2 % - weekly batch"}\n')
        for key, d in (('companies_and_funds', {n: v for n, v in inst.items() if meta[n]['cls'] not in ('cash',)}), ('commodities', comm), ('regions', reg), ('themes', theme)):
            fh.write(f'{key}:\n')
            for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:60]:
                fh.write(f'  - {{name: "{k}", weight_pct: {v/tot*100:.2f}, tier: {tier(v/tot*100)}}}\n')
    c = defaultdict(int)
    for t, *_ in U: c[t] += 1
    print('queries', len(U), dict(c))

if __name__ == '__main__':
    main(*sys.argv[1:4])

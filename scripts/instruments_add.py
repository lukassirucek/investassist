#!/usr/bin/env python3
"""Add or replace one row in data/reference/instruments.csv (classification used by the exposure map). Avoids hand-editing CSV quoting.

Usage: python3 -I scripts/instruments_add.py --ids "ISIN|SYMBOL|Exact name used by an index" --name "Display name" --class equity_single \
         --sector "Information Technology" --industry Semiconductors --sub "AI GPUs" --hq US --regions "US;Taiwan" --materials "silicon wafers;copper" --themes "AI;semis"
class: equity_single | equity_etf | bond_etf | fund | crypto | gold | loan | cert | cash.  ETFs: sector "Diversified", industry "ETF", sub_industry = the index name.
`ids` are matched case-insensitively against the index rows' instrument_id, symbol and name. Special keys: `platform:<platform>:<asset_class>` (all rows of that kind on a platform), `cash:<ccy>`, `cash`.
Identify instruments from their ISIN with a web search; never guess from a ticker.
"""
import argparse, csv, os

P = 'data/reference/instruments.csv'
COLS = ['ids', 'name', 'class', 'sector', 'industry', 'sub_industry', 'hq', 'revenue_regions', 'raw_materials', 'themes']
ap = argparse.ArgumentParser()
ap.add_argument('--ids', required=True); ap.add_argument('--name', required=True); ap.add_argument('--class', dest='cls', required=True)
for k in ('sector', 'industry', 'sub', 'hq', 'regions', 'materials', 'themes'):
    ap.add_argument('--' + k, default='')
a = ap.parse_args()
rows = list(csv.DictReader(open(P, encoding='utf-8'))) if os.path.exists(P) else []
new = dict(ids=a.ids, name=a.name, **{'class': a.cls}, sector=a.sector, industry=a.industry, sub_industry=a.sub, hq=a.hq, revenue_regions=a.regions, raw_materials=a.materials, themes=a.themes)
mine = {x.strip().lower() for x in a.ids.split('|')}
rows = [r for r in rows if not ({x.strip().lower() for x in r['ids'].split('|')} & mine)] + [new]
os.makedirs(os.path.dirname(P), exist_ok=True)
with open(P, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
print(f'{len(rows)} instruments; saved {a.name}')

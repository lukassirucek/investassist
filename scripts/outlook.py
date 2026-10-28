#!/usr/bin/env python3
"""Top-N holdings outlook: selection, validation, track record.

  python3 -I scripts/outlook.py top [N]                 # pick the N largest non-cash holdings, write data/outlook/top15.csv with search queries
  python3 -I scripts/outlook.py ingest <calls.json> [YYYY-MM-DD]   # validate a run's calls, store data/outlook/<date>_outlook.json + latest.json, log them
  python3 -I scripts/outlook.py missing [YYYY-MM-DD]    # top-N instruments without a call in that run
  python3 -I scripts/outlook.py due [YYYY-MM-DD]        # logged calls whose horizon ended and have no outcome yet
  python3 -I scripts/outlook.py outcome <run_date> <instrument> <pct>   # record the realised price change (%) for a call
  python3 -I scripts/outlook.py score                   # hit rate by lean and confidence

calls.json = list of objects:
  instrument (exact name from top15.csv), summary (1-2 sentences), horizon_days (default 28), ref_price / price_ccy (optional, for the track record),
  drivers: [{text, direction: pos|neg|neutral, weight: 1-3, kind: news|company|press_release|analyst|macro, source_url, source_date}],
  catalysts: [{date, event}], risks: [str]
The script computes score = sum(sign x weight) over SOURCED drivers, lean (up if score >= threshold, down if <= -threshold, else neutral) and caps confidence by evidence:
  high needs >= 3 sourced drivers from >= 2 domains, medium needs >= 2 from >= 2 domains, otherwise low. A lean is a tilt from dated news, not a forecast.
"""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER, BASE
from collections import defaultdict
from urllib.parse import urlparse
import yaml

OUT = 'data/outlook'
LOG = f'{OUT}/outlook_log.csv'
LOG_COLS = ['run_date', 'instrument', 'lean', 'score', 'confidence', 'horizon_end', 'ref_price', 'price_ccy', 'outcome_pct']


def cfg():
    try:
        return yaml.safe_load(open('config/playbook.yaml', encoding='utf-8')).get('outlook', {})
    except Exception:
        return {}


def holdings_agg():
    rows = [r for r in csv.DictReader(open('data/exposure/holdings_enriched.csv', encoding='utf-8')) if r['owner'] == OWNER]
    tot = sum(float(r['value_base']) for r in rows)
    g = {}
    for r in rows:
        if r['cls'] == 'cash':
            continue
        a = g.setdefault(r['instrument'], dict(instrument=r['instrument'], cls=r['cls'], value=0.0, platforms=set(), refs=set(), sector=r['sector'], industry=r['industry'],
                                              sub=r['sub_industry'], themes=r['themes'], hq=r['hq']))
        a['value'] += float(r['value_base']); a['platforms'].add(r['platform'])
        a['refs'] |= {x for x in r['ref_ids'].split(';') if x}
    return sorted(g.values(), key=lambda a: -a['value']), tot


def queries(a, month):
    n, c = a['instrument'], a['cls']
    topic = a['sub'] if a['sub'] not in ('', 'n/a') else a['sector']
    if c == 'equity_single':
        return ([f'{n} stock news {month}', f'{n} analyst rating price target {month}'], [f'{n} results guidance earnings date', f'{n} company announcement'], [f'{n} press release', f'{n} investor relations'])
    if c in ('equity_etf', 'bond_etf', 'fund', 'cert'):
        return ([f'{n} index outlook {month}', f'{topic} market news {month}'], [f'{n} top holdings news', f'{n} fund flows'], [f'{n} issuer announcement', f'{n} index methodology change'])
    if c == 'crypto':
        return ([f'{n} price news {month}', f'{n} ETF flows regulation {month}'], [f'{n} miners treasury companies news'], [f'{n} regulatory announcement SEC'])
    if c == 'gold':
        return ([f'gold price outlook {month}', 'central bank gold buying Fed gold'], ['World Gold Council demand report', 'gold ETF flows'], ['Goldman Sachs UBS gold forecast'])
    if c == 'loan':
        return ([f'{n} platform news', f'{n} defaults delays', 'property market mortgage rates'], [f'{n} company news', 'central bank rate decision'], [f'{n} press release', f'{n} regulator announcement'])
    return ([f'{n} news {month}'], [f'{n} company news'], [f'{n} press release'])


def top(n=None):
    n = int(n or cfg().get('top_n', 15))
    agg, tot = holdings_agg()
    month = dt.date.today().strftime('%B %Y')
    os.makedirs(OUT, exist_ok=True)
    with open(f'{OUT}/top15.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['rank', 'instrument', 'cls', 'value_base', 'pct_total', 'platforms', 'ref_ids', 'sector', 'industry', 'sub_industry', 'q_news', 'q_company', 'q_press_release'])
        for i, a in enumerate(agg[:n], 1):
            q = queries(a, month)
            w.writerow([i, a['instrument'], a['cls'], round(a['value']), round(a['value'] / tot * 100, 2), ';'.join(sorted(a['platforms'])), ';'.join(sorted(a['refs'])), a['sector'], a['industry'], a['sub'],
                        ' || '.join(q[0]), ' || '.join(q[1]), ' || '.join(q[2])])
            print(f"{i:>2} {a['instrument'][:44]:44} {a['cls']:13} {a['value']:>10,.0f} {BASE} {a['value'] / tot * 100:5.1f} %  {','.join(sorted(a['platforms']))}")
    print(f'top {n} -> {OUT}/top15.csv')


def top_rows():
    p = f'{OUT}/top15.csv'
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def ingest(path, day=None):
    day = day or dt.date.today().isoformat()
    c = cfg(); thr = int(c.get('lean_threshold', 3)); hd = int(c.get('horizon_days', 28))
    known = {r['instrument'] for r in top_rows()}
    items, warn = [], []
    for it in json.load(open(path, encoding='utf-8')):
        name = it.get('instrument', '')
        if known and name not in known:
            warn.append(f'{name}: not in top15.csv, skipped'); continue
        dr = []
        for d in it.get('drivers', []):
            ok = str(d.get('source_url', '')).startswith('http') and d.get('source_date')
            if not ok:
                warn.append(f"{name}: driver without source url/date ignored: {str(d.get('text', ''))[:50]}"); continue
            dr.append(dict(text=d['text'], direction=d.get('direction', 'neutral'), weight=max(1, min(3, int(d.get('weight', 1)))), kind=d.get('kind', 'news'),
                           source_url=d['source_url'], source_date=d['source_date']))
        score = sum({'pos': 1, 'neg': -1}.get(d['direction'], 0) * d['weight'] for d in dr)
        lean = 'up' if score >= thr else 'down' if score <= -thr else 'neutral'
        doms = {urlparse(d['source_url']).netloc.replace('www.', '') for d in dr}
        conf = 'high' if len(dr) >= 3 and len(doms) >= 2 else 'medium' if len(dr) >= 2 and len(doms) >= 2 else 'low'
        asked = it.get('confidence')
        if asked and ['low', 'medium', 'high'].index(asked) > ['low', 'medium', 'high'].index(conf):
            warn.append(f'{name}: confidence {asked} capped to {conf} (sourced drivers {len(dr)}, domains {len(doms)})')
        h = int(it.get('horizon_days', hd))
        items.append(dict(instrument=name, lean=lean, score=score, confidence=conf, horizon_days=h, horizon_end=(dt.date.fromisoformat(day) + dt.timedelta(days=h)).isoformat(),
                          summary=it.get('summary', ''), drivers=dr, catalysts=it.get('catalysts', []), risks=it.get('risks', []), ref_price=it.get('ref_price'), price_ccy=it.get('price_ccy', '')))
    os.makedirs(OUT, exist_ok=True)
    doc = dict(run_date=day, items=items)
    json.dump(doc, open(f'{OUT}/{day}_outlook.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(doc, open(f'{OUT}/latest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cur = list(csv.DictReader(open(LOG, encoding='utf-8'))) if os.path.exists(LOG) else []
    seen = {(r['run_date'], r['instrument']) for r in cur}
    new = [dict(run_date=day, instrument=i['instrument'], lean=i['lean'], score=i['score'], confidence=i['confidence'], horizon_end=i['horizon_end'], ref_price=i['ref_price'] or '',
                price_ccy=i['price_ccy'], outcome_pct='') for i in items if (day, i['instrument']) not in seen]
    fresh = not os.path.exists(LOG) or os.path.getsize(LOG) == 0
    with open(LOG, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS)
        if fresh:
            w.writeheader()
        w.writerows(new)
    for w_ in warn:
        print('WARN', w_)
    print(f'{len(items)} calls stored ({len(new)} new in log): up {sum(i["lean"] == "up" for i in items)}, down {sum(i["lean"] == "down" for i in items)}, neutral {sum(i["lean"] == "neutral" for i in items)}')


def missing(day=None):
    day = day or dt.date.today().isoformat()
    p = f'{OUT}/{day}_outlook.json'
    have = {i['instrument'] for i in json.load(open(p, encoding='utf-8'))['items']} if os.path.exists(p) else set()
    m = [r['instrument'] for r in top_rows() if r['instrument'] not in have]
    print('missing: ' + (', '.join(m) if m else 'none'))


def due(day=None):
    day = day or dt.date.today().isoformat()
    rows = list(csv.DictReader(open(LOG, encoding='utf-8'))) if os.path.exists(LOG) else []
    d = [r for r in rows if r['horizon_end'] <= day and not r['outcome_pct']]
    for r in d:
        print(f"{r['run_date']} | {r['instrument']} | {r['lean']} ({r['score']}) | ref {r['ref_price']} {r['price_ccy']} | horizon ended {r['horizon_end']}")
    print(f'{len(d)} calls awaiting an outcome')


def outcome(run_date, instrument, pct):
    rows = list(csv.DictReader(open(LOG, encoding='utf-8')))
    hit = 0
    for r in rows:
        if r['run_date'] == run_date and r['instrument'] == instrument:
            r['outcome_pct'] = str(float(pct)); hit += 1
    with open(LOG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS); w.writeheader(); w.writerows(rows)
    print(f'{hit} row updated')


def calibration():
    rows = [r for r in csv.DictReader(open(LOG, encoding='utf-8')) if r['outcome_pct']] if os.path.exists(LOG) else []
    def is_hit(r):
        o = float(r['outcome_pct'])
        return (r['lean'] == 'up' and o > 0) or (r['lean'] == 'down' and o < 0) or (r['lean'] == 'neutral' and abs(o) < 3)
    out = dict(n=len(rows), hits=sum(is_hit(r) for r in rows), by_lean={}, by_conf={})
    for key, name in (('lean', 'by_lean'), ('confidence', 'by_conf')):
        g = defaultdict(list)
        for r in rows:
            g[r[key]].append(is_hit(r))
        out[name] = {k: dict(n=len(v), hits=sum(v)) for k, v in g.items()}
    return out


def score():
    c = calibration()
    if not c['n']:
        print('no scored calls yet (record outcomes with: outlook.py outcome <run_date> <instrument> <pct>)'); return
    print(f"{c['hits']}/{c['n']} hits ({c['hits'] / c['n'] * 100:.0f} %). Hit = up and price rose, down and price fell, neutral and |move| < 3 %. Small samples mean little.")
    for k in ('by_lean', 'by_conf'):
        for name, v in c[k].items():
            print(f"  {k[3:]} {name}: {v['hits']}/{v['n']}")


if __name__ == '__main__':
    a = sys.argv[1:]
    cmds = {'top': top, 'ingest': ingest, 'missing': missing, 'due': due, 'outcome': outcome, 'score': score}
    if not a or a[0] not in cmds:
        print(__doc__)
    else:
        cmds[a[0]](*a[1:])

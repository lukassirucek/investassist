#!/usr/bin/env python3
"""Signal log + impact projection + daily digest.
  python3 -I scripts/signals.py ingest <new_signals.json>     # append signals (dedup on source_url+headline)
  python3 -I scripts/signals.py digest [YYYY-MM-DD]           # write data/reports/<date>/daily_digest.md from the log + holdings
  python3 -I scripts/signals.py project                       # print active signals ranked by estimated impact in the base currency
Signal fields (JSON list): event_date, category (company|commodity|geopolitics|sanctions|macro|hazard|housing|platform), headline, source_url, source_date, severity 1-5,
  direction (neg|pos|mixed), horizon_days (when impact is expected to show, from event_date), tags (list; use prefixes theme:/raw:/region:/name:/class:/sector:/sub: to avoid over-matching, plain tag matches any field),
  basis (FACT|INFERENCE|HISTORICAL PATTERN), summary, impact_low_pct, impact_high_pct (price move on tagged holdings, signed from the portfolio's point of view), confidence (low|medium|high)
Impact (base currency) = sum(value of holdings matching any tag) x pct. Estimates are scenario ranges, not forecasts. Action candidates come from config/playbook.yaml and are for review only.
"""
import csv, datetime as dt, hashlib, json, os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER, BASE

SIG = 'data/signals/signals.csv'
COLS = ['signal_id', 'date_logged', 'event_date', 'category', 'headline', 'source_url', 'source_date', 'severity', 'direction', 'horizon_days', 'tags', 'basis', 'summary',
        'impact_low_pct', 'impact_high_pct', 'confidence', 'status']

def load_signals():
    return list(csv.DictReader(open(SIG, encoding='utf-8'))) if os.path.exists(SIG) else []

def holdings():
    E = [e for e in csv.DictReader(open('data/exposure/holdings_enriched.csv', encoding='utf-8')) if e['owner'] == OWNER]
    for e in E:
        e['v'] = float(e['value_base'])
        toks = {'name:' + e['instrument'].lower(), 'sector:' + e['sector'].lower(), 'industry:' + e['industry'].lower(), 'sub:' + e['sub_industry'].lower(), 'class:' + e['cls'].lower(), 'region:' + e['hq'].lower()}
        toks |= {'region:' + x.strip().lower() for x in e['revenue_regions'].split(';') if x.strip()}
        toks |= {'raw:' + x.strip().lower() for x in e['raw_materials'].split(';') if x.strip()}
        toks |= {'theme:' + x.strip().lower() for x in e['themes'].split(';') if x.strip()}
        e['toks'] = toks
        e['plain'] = {t.split(':', 1)[1] for t in toks}
    return E

def match(E, tags):
    """Tag syntax: 'theme:gold', 'raw:aluminium', 'region:CZ', 'name:Rheinmetall', 'class:gold', 'sector:Energy', 'sub:S&P 500'; a plain tag matches any field."""
    t = [x.strip().lower() for x in tags if x.strip()]
    pre = {x for x in t if ':' in x}; plain = {x for x in t if ':' not in x}
    return [e for e in E if (e['toks'] & pre) or (e['plain'] & plain)]

def ingest(path):
    new = json.load(open(path, encoding='utf-8'))
    cur = load_signals(); seen = {(s['source_url'], s['headline']) for s in cur}
    os.makedirs(os.path.dirname(SIG), exist_ok=True)
    add = []
    for n in new:
        if (n['source_url'], n['headline']) in seen: continue
        sid = hashlib.sha1((n['source_url'] + n['headline']).encode()).hexdigest()[:8]
        add.append(dict(signal_id=sid, date_logged=dt.date.today().isoformat(), event_date=n.get('event_date', dt.date.today().isoformat()), category=n['category'], headline=n['headline'],
                        source_url=n['source_url'], source_date=n.get('source_date', ''), severity=n['severity'], direction=n['direction'], horizon_days=n.get('horizon_days', 30),
                        tags=';'.join(n['tags']), basis=n.get('basis', 'INFERENCE'), summary=n.get('summary', ''), impact_low_pct=n.get('impact_low_pct', 0), impact_high_pct=n.get('impact_high_pct', 0),
                        confidence=n.get('confidence', 'low'), status='active'))
    new_file = not os.path.exists(SIG)
    with open(SIG, 'a', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new_file: w.writeheader()
        w.writerows(add)
    print(f'ingested {len(add)} new signals ({len(new) - len(add)} duplicates skipped)')

def evaluate(s, E, tot, pb):
    m = match(E, s['tags'].split(';'))
    exp = sum(e['v'] for e in m)
    lo, hi = float(s['impact_low_pct']) / 100, float(s['impact_high_pct']) / 100
    mid = (lo + hi) / 2
    d = dt.date.fromisoformat(s['event_date']) + dt.timedelta(days=int(float(s['horizon_days'])))
    pct = exp / tot * 100
    th = pb['thresholds']
    alert = int(s['severity']) >= th['alert_severity'] or abs(exp * mid / tot * 100) >= th['alert_impact_pct']
    acts = []
    for r in pb['rules']:
        w = r['when']
        if w.get('direction') != s['direction']: continue
        if int(s['severity']) < w.get('min_severity', 0): continue
        if pct < w.get('min_exposure_pct', 0) or pct > w.get('max_exposure_pct', 1e9): continue
        acts.append((r['id'], r['action']))
    return dict(s, matched=m, exposure=exp, exposure_pct=pct, impact_lo=exp * lo, impact_hi=exp * hi, impact_mid_pct=exp * mid / tot * 100, due=d, alert=alert, actions=acts)

def digest(day):
    pb = yaml.safe_load(open('config/playbook.yaml', encoding='utf-8'))
    E = holdings(); tot = sum(e['v'] for e in E)
    S = [evaluate(s, E, tot, pb) for s in load_signals() if s['status'] == 'active']
    today = dt.date.fromisoformat(day)
    S.sort(key=lambda s: (not s['alert'], -abs(s['impact_mid_pct'])))
    os.makedirs(f'data/reports/{day}', exist_ok=True)
    L = [f'# Daily digest {day}\n\nOwn portfolio {tot:,.0f} {BASE} | active signals {len(S)} | alerts {sum(1 for s in S if s["alert"])}\n']
    L.append('> Scenario ranges and action candidates are for your review, not predictions or financial advice. Each item shows FACT/INFERENCE/HISTORICAL PATTERN.\n')
    for title, items in (('ALERTS', [s for s in S if s['alert']]), ('WATCH', [s for s in S if not s['alert']])):
        L.append(f'\n## {title} ({len(items)})\n')
        for s in items:
            names = ', '.join(sorted({e['instrument'] for e in s['matched']}, key=lambda n: -sum(e['v'] for e in s['matched'] if e['instrument'] == n))[:6]) or 'none matched'
            L.append(f"### [{s['category']}] {s['headline']}\n- severity {s['severity']}/5, {s['direction']}, confidence {s['confidence']}, basis {s['basis']}; event {s['event_date']}, impact expected by **{s['due']}**\n"
                     f"- source: {s['source_url']} ({s['source_date']})\n- {s['summary']}\n- exposure matched: {s['exposure']:,.0f} {BASE} ({s['exposure_pct']:.1f} % of portfolio) - {names}\n"
                     f"- scenario impact: {s['impact_lo']:,.0f} to {s['impact_hi']:,.0f} {BASE} ({float(s['impact_low_pct']):+.1f} % to {float(s['impact_high_pct']):+.1f} % on exposure)\n")
            for rid, a in s['actions']: L.append(f'- action candidate {rid}: {a}\n')
    L.append(f'\n## Impact timeline (when each active signal is expected to show)\n| expected by | signal | exposure {BASE} | scenario {BASE} |\n|---|---|---:|---|\n')
    for s in sorted(S, key=lambda s: s['due']): L.append(f"| {s['due']} | {s['headline'][:70]} | {s['exposure']:,.0f} | {s['impact_lo']:,.0f} to {s['impact_hi']:,.0f} |\n")
    net_lo = sum(s['impact_lo'] if s['impact_lo'] < s['impact_hi'] else s['impact_hi'] for s in S); net_hi = sum(max(s['impact_lo'], s['impact_hi']) for s in S)
    L.append(f'\nSum of scenario ranges (signals overlap, so this overstates a net effect): {net_lo:,.0f} to {net_hi:,.0f} {BASE}.\n')
    open(f'data/reports/{day}/daily_digest.md', 'w', encoding='utf-8').write(''.join(L))
    print(f'digest written: data/reports/{day}/daily_digest.md ({len(S)} signals, {sum(1 for s in S if s["alert"])} alerts)')

def project():
    pb = yaml.safe_load(open('config/playbook.yaml', encoding='utf-8'))
    E = holdings(); tot = sum(e['v'] for e in E)
    for s in sorted((evaluate(s, E, tot, pb) for s in load_signals() if s['status'] == 'active'), key=lambda s: -abs(s['impact_mid_pct'])):
        print(f"{s['due']} | {s['headline'][:60]:60} | exp {s['exposure']:>9,.0f} | mid {s['impact_mid_pct']:+.2f} % of portfolio")

if __name__ == '__main__':
    c = sys.argv[1] if len(sys.argv) > 1 else ''
    if c == 'ingest': ingest(sys.argv[2])
    elif c == 'digest': digest(sys.argv[2] if len(sys.argv) > 2 else dt.date.today().isoformat())
    elif c == 'project': project()
    else: print(__doc__)

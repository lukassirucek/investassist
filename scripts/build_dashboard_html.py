#!/usr/bin/env python3
"""Daily dashboard: what the news touches in the portfolio, the top-15 outlook, catalysts, mail events, data freshness.

Usage (repo root):  python3 -I scripts/build_dashboard_html.py [YYYY-MM-DD]

Reads   data/signals/signals.csv + data/exposure/holdings_enriched.csv + config/playbook.yaml   (via scripts/signals.py evaluate)
        data/outlook/latest.json, data/outlook/top15.csv, data/outlook/outlook_log.csv           (scripts/outlook.py)
        data/ledger/mail_events.csv                                                               (scripts/mail_events.py)
        data/index/*.index.md                                                                     (valuation dates)
Writes  data/reports/<date>/dashboard.html            standalone page
        data/reports/<date>/dashboard.artifact.html   fragment for the Artifact tool
No network needed (no chart library; bars are CSS). Scenario ranges and leans are tilts from dated sources, not forecasts or advice.
"""
import csv, datetime as dt, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
import htmlkit as H
from common import BASE, DEMO
import signals as SG
import outlook as OL
from htmlkit import esc, money, kmoney

TODAY = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
TD = dt.date.fromisoformat(TODAY)
STALE_DAYS = 35
LEAN = {'up': ('&#9650;', 'Up', 'up'), 'down': ('&#9660;', 'Down', 'down'), 'neutral': ('&#9679;', 'Neutral', 'neu')}
DIRW = {'neg': ('&#9660;', 'Negative', 'down'), 'pos': ('&#9650;', 'Positive', 'up'), 'mixed': ('&#9670;', 'Mixed', 'neu')}


def lean_html(l):
    g, w, c = LEAN.get(l, LEAN['neutral'])
    return f'<span class="lean {c}">{g} {w}</span>'


def src_link(url, text='source'):
    if url.startswith('http') and 'mail.google.com' not in url:
        return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'
    return f'<span class="hint" style="display:inline">{"e-mail" if "mail.google" in url else "own file"}</span>'


def load():
    pb = yaml.safe_load(open('config/playbook.yaml', encoding='utf-8'))
    E = SG.holdings(); tot = sum(e['v'] for e in E)
    S = [SG.evaluate(s, E, tot, pb) for s in SG.load_signals() if s['status'] == 'active']
    S.sort(key=lambda s: (not s['alert'], -abs(s['impact_mid_pct'])))
    return pb, E, tot, S


def affected(S, E, tot):
    """Aggregate by instrument: value, signals touching it, summed scenario range."""
    val = {}
    for e in E:
        if e['cls'] == 'cash':
            continue
        val[e['instrument']] = val.get(e['instrument'], 0) + e['v']
    A = {}
    for s in S:
        lo, hi = float(s['impact_low_pct']) / 100, float(s['impact_high_pct']) / 100
        per = {}
        for e in s['matched']:
            per[e['instrument']] = per.get(e['instrument'], 0) + e['v']
        for name, v in per.items():
            a = A.setdefault(name, dict(name=name, value=val.get(name, v), sigs=[], lo=0.0, hi=0.0, alerts=0))
            a['sigs'].append(s); a['lo'] += v * min(lo, hi); a['hi'] += v * max(lo, hi); a['alerts'] += 1 if s['alert'] else 0
    return sorted(A.values(), key=lambda a: -max(abs(a['lo']), abs(a['hi'])))


def load_outlook():
    p = 'data/outlook/latest.json'
    doc = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else dict(run_date='', items=[])
    top = {r['instrument']: r for r in OL.top_rows()}
    for i in doc['items']:
        t = top.get(i['instrument'], {})
        i['value'] = float(t.get('value_base') or 0); i['pct'] = float(t.get('pct_total') or 0); i['rank'] = int(t.get('rank') or 99)
    doc['items'].sort(key=lambda i: i['rank'])
    return doc


def mail_rows(days=30):
    cut = (TD - dt.timedelta(days=days)).isoformat()
    p = 'data/ledger/mail_events.csv'
    rows = list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []
    return sorted([r for r in rows if r['date'] >= cut], key=lambda r: r['date'], reverse=True)


def freshness():
    out = []
    for p in sorted(glob.glob('data/index/*.index.md')):
        name = os.path.basename(p).replace('.index.md', '')
        if name == 'master':
            continue
        head = open(p, encoding='utf-8').read(1500)
        d = None
        for pat in (r'^valuation_date:\s*(\d{4}-\d{2}-\d{2})', r'^statement_position_date:\s*(\d{4}-\d{2}-\d{2})', r'^(?:statement_period|period):\s*.*?(\d{4}-\d{2}-\d{2})\s*$'):
            m = re.search(pat, head, re.M)
            if m:
                d = dt.date.fromisoformat(m.group(1)); break
        out.append((name, d, (TD - d).days if d else None))
    return sorted(out, key=lambda x: -(x[2] if x[2] is not None else 9999))


def catalysts(S, O, M, horizon=14):
    end = TD + dt.timedelta(days=horizon)
    seen, ev = set(), []
    def add(d, text, kind, who=''):
        try:
            dd = dt.date.fromisoformat(d)
        except Exception:
            return
        if TD <= dd <= end and (d, text) not in seen:
            seen.add((d, text)); ev.append((d, text, kind, who))
    for i in O['items']:
        for c in i.get('catalysts', []):
            add(c.get('date', ''), c.get('event', ''), 'outlook', i['instrument'])
    keys = ('FOMC', 'ECB', 'CNB', 'PCE', 'Amazon', 'BoJ')
    for s in S:
        k = next((k for k in keys if k.lower() in s['headline'].lower()), None)
        if k and any(d == s['event_date'] and k.lower() in t.lower() for d, t, _, _ in ev):
            continue  # same event already listed from the outlook
        add(s['event_date'], s['headline'], 'signal', '')
    for r in M:
        if r['deadline']:
            add(r['deadline'], f"{r['source']}: {r['subject']}", 'mail', '')
    # same event listed by several holdings: merge the holdings
    merged = {}
    for d, t, k, w in ev:
        m = merged.setdefault((d, t, k), [])
        if w:
            m.append(w)
    return sorted([(d, t, k, ws) for (d, t, k), ws in merged.items()], key=lambda x: (x[0], x[2]))


def score_bar(score, cap=6):
    w = min(abs(score), cap) / cap * 50
    if score == 0:
        return '<span class="sc" role="img" aria-label="score 0"><u></u></span>'
    left = 50 if score > 0 else 50 - w
    col = 'var(--up)' if score > 0 else 'var(--down)'
    return f'<span class="sc" role="img" aria-label="score {score:+d}"><i style="left:{left:.1f}%;width:{w:.1f}%;background:{col}"></i><u></u></span>'


def build():
    pb, E, tot, S = load()
    O = load_outlook(); A = affected(S, E, tot); M = mail_rows(); F = freshness(); CAL = catalysts(S, O, M)
    cal = OL.calibration()
    lean_by = {i['instrument']: i for i in O['items']}
    alerts = [s for s in S if s['alert']]
    touched = {id(e): e['v'] for s in S for e in s['matched'] if e['cls'] != 'cash'}
    touched_v = sum(touched.values())
    lo_sum = sum(min(s['impact_lo'], s['impact_hi']) for s in S); hi_sum = sum(max(s['impact_lo'], s['impact_hi']) for s in S)
    n_up = sum(i['lean'] == 'up' for i in O['items']); n_dn = sum(i['lean'] == 'down' for i in O['items']); n_ne = len(O['items']) - n_up - n_dn
    need = [r for r in M if r['action'] in ('review', 'urgent')]
    stale = [f for f in F if f[2] is not None and f[2] > STALE_DAYS]

    # --- tiles
    tiles = [
        ('Alerts', f'{len(alerts)}', f'of {len(S)} active signals'),
        ('Exposure touched', f'{touched_v / tot * 100:.1f} %', f'{money(touched_v)} {BASE} in at least one signal'),
        ('Scenario range', f'{kmoney(lo_sum)} to {kmoney(hi_sum)}', f'{BASE}, summed over overlapping signals; not a forecast'),
        (f'Outlook {O["run_date"] or "-"}', f'&#9650;{n_up} &#9660;{n_dn} &#9679;{n_ne}', f'{len(O["items"])} largest holdings, {pb.get("outlook", {}).get("horizon_days", 28)} day lean'),
        ('Mail, last 30 days', f'{len(M)}', f'{len(need)} need a look'),
        ('Outlook track record', f'{cal["hits"]}/{cal["n"]}' if cal['n'] else 'none yet', 'hits among scored calls' if cal['n'] else 'scores appear once horizons end'),
    ]
    tiles_html = ''.join(f'<div class="stat"><div class="k">{esc(k)}</div><div class="n">{v}</div><div class="s">{esc(s)}</div></div>' for k, v, s in tiles)

    # --- attention box
    att = []
    for s in alerts:
        names = ', '.join(sorted({e['instrument'] for e in s['matched']}, key=lambda n: -sum(e['v'] for e in s['matched'] if e['instrument'] == n))[:3])
        att.append(f'<li><span class="alert">&#9888; Alert</span> {esc(s["headline"])} <span class="hint" style="display:inline">({s["exposure_pct"]:.1f} % of total: {esc(names)})</span></li>')
    for r in need:
        att.append(f'<li><span class="alert">&#9993; Mail</span> {esc(r["source"])}: {esc(r["subject"])} <span class="hint" style="display:inline">({esc(r["date"])}{", deadline " + esc(r["deadline"]) if r["deadline"] else ""})</span></li>')
    for i in O['items']:
        if i['lean'] != 'neutral':
            att.append(f'<li>{lean_html(i["lean"])} <b>{esc(i["instrument"])}</b> {esc(i["summary"])}</li>')
    for d, t, k, ws in CAL:
        if (dt.date.fromisoformat(d) - TD).days <= 1 and k == 'outlook':
            att.append(f'<li><span class="chip">{esc(d)}</span> {esc(t)}</li>')
    if stale:
        att.append(f'<li><span class="alert">&#9888; Stale data</span> {", ".join(esc(f[0]) + " (" + str(f[2]) + " d)" for f in stale)}</li>')
    att_html = ('<ul class="dr">' + ''.join(att[:12]) + '</ul>') if att else '<p class="hint">Nothing needs attention.</p>'

    # --- signals
    sig = []
    for s in S:
        g, w, c = DIRW.get(s['direction'], DIRW['mixed'])
        by = {}
        for e in s['matched']:
            by[e['instrument']] = by.get(e['instrument'], 0) + e['v']
        pos = ''.join(f'<li>{esc(n)} <span class="mono">{money(v)} {BASE}</span> ({v / tot * 100:.1f} %)</li>' for n, v in sorted(by.items(), key=lambda x: -x[1])[:12]) or '<li>no holding matched</li>'
        acts = ''.join(f'<li>{esc(rid)}: {esc(a)}</li>' for rid, a in s['actions'])
        sig.append(
            f'<details class="it" data-alert="{1 if s["alert"] else 0}"><summary><span class="t">{"<span class=alert>&#9888;</span> " if s["alert"] else ""}{esc(s["headline"])}</span>'
            f'<span class="mono hint">{money(s["impact_lo"] if s["impact_lo"] < s["impact_hi"] else s["impact_hi"])} to {money(max(s["impact_lo"], s["impact_hi"]))} {BASE}</span>'
            f'<span><span class="chip">{esc(s["category"])}</span> <span class="lean {c}">{g} {w}</span> <span class="hint" style="display:inline">sev {esc(s["severity"])}/5 &middot; {s["exposure_pct"]:.1f} % of total &middot; by {esc(s["due"])}</span></span><span></span></summary>'
            f'<div class="body"><p>{esc(s["summary"])}</p><p class="hint">{esc(s["basis"])} &middot; confidence {esc(s["confidence"])} &middot; {src_link(s["source_url"], "source " + s["source_date"])}</p>'
            f'<p><b>Positions touched</b></p><ul class="dr">{pos}</ul>' + (f'<p><b>Action candidates (for review)</b></p><ul class="dr">{acts}</ul>' if acts else '') + '</div></details>')
    sig_html = ''.join(sig) or '<p class="hint">No active signals.</p>'

    # --- affected positions
    rows = []
    for a in A:
        o = lean_by.get(a['name'])
        sigtxt = '<br>'.join(esc(s['headline'][:70]) for s in a['sigs'][:3]) + (f'<br>+{len(a["sigs"]) - 3} more' if len(a['sigs']) > 3 else '')
        lean = o['lean'] if o else ''
        rows.append(
            f'<tr data-alert="{1 if a["alerts"] else 0}" data-lean="{esc(lean)}"><td class="w" data-v="{esc(a["name"].lower())}">{esc(a["name"])}<span class="hint">{sigtxt}</span></td>'
            f'<td class="r mono" data-v="{a["value"]:.0f}">{money(a["value"])}</td><td class="r mono" data-v="{a["value"] / tot * 100:.3f}">{a["value"] / tot * 100:.1f}</td>'
            f'<td class="r mono" data-v="{len(a["sigs"])}">{len(a["sigs"])}{" (" + str(a["alerts"]) + " alert)" if a["alerts"] else ""}</td>'
            f'<td class="r mono" data-v="{a["lo"]:.0f}">{money(a["lo"], True)}</td><td class="r mono" data-v="{a["hi"]:.0f}">{money(a["hi"], True)}</td>'
            f'<td data-v="{esc(lean)}">{lean_html(lean) if o else "<span class=hint>not in top 15</span>"}</td></tr>')
    pos_html = ('<div class="tw"><table class="sortable" id="tpos"><thead><tr>'
                f'<th><button data-c="0">Position</button></th><th class="r"><button data-c="1">Value {BASE}</button></th><th class="r"><button data-c="2">% total</button></th>'
                f'<th class="r"><button data-c="3">Signals</button></th><th class="r"><button data-c="4">Low {BASE}</button></th><th class="r"><button data-c="5">High {BASE}</button></th><th><button data-c="6">Outlook</button></th>'
                f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>') if rows else '<p class="hint">No position matched an active signal.</p>'

    # --- outlook
    orows, odet = [], []
    for i in O['items']:
        dr = ''.join(f'<li><span class="lean {"up" if d["direction"] == "pos" else "down" if d["direction"] == "neg" else "neu"}">{"&#9650;" if d["direction"] == "pos" else "&#9660;" if d["direction"] == "neg" else "&#9679;"} w{d["weight"]}</span> '
                     f'{esc(d["text"])} <span class="hint" style="display:inline">({src_link(d["source_url"], d["kind"] + " " + d["source_date"])})</span></li>' for d in i['drivers'])
        ca = ''.join(f'<li>{esc(c.get("date", ""))}: {esc(c.get("event", ""))}</li>' for c in i.get('catalysts', []))
        rk = ''.join(f'<li>{esc(r)}</li>' for r in i.get('risks', []))
        orows.append(
            f'<details class="it"><summary><span class="t">{esc(i["instrument"])} <span class="hint" style="display:inline">{money(i["value"])} {BASE} &middot; {i["pct"]:.1f} %</span></span>'
            f'<span>{lean_html(i["lean"])} {score_bar(i["score"])} <span class="mono hint" style="display:inline">{i["score"]:+d}</span> <span class="chip" title="sourced drivers and distinct domains">evidence {esc(i["confidence"])}</span></span>'
            f'<span class="hint" style="grid-column:1/-1">{esc(i["summary"])}</span></summary>'
            f'<div class="body"><p><b>Drivers</b> (score = sum of direction x weight; lean needs |score| &ge; {pb.get("outlook", {}).get("lean_threshold", 3)})</p><ul class="dr">{dr}</ul>'
            + (f'<p><b>Catalysts</b></p><ul class="dr">{ca}</ul>' if ca else '') + (f'<p><b>Risks</b></p><ul class="dr">{rk}</ul>' if rk else '')
            + f'<p class="hint">Horizon to {esc(i["horizon_end"])}. A tilt from dated sources, not a price forecast.</p></div></details>')
    out_html = ''.join(orows) or '<p class="hint">No outlook run yet: run scripts/outlook.py.</p>'

    # --- calendar
    cal_html = '<ul class="cl">' + ''.join(
        f'<li><span class="mono">{esc(d)}<span class="hint">{"today" if d == TODAY else "in " + str((dt.date.fromisoformat(d) - TD).days) + " d"}</span></span>'
        f'<span>{esc(t)}{" <span class=hint style=display:inline>(" + esc(", ".join(ws[:4])) + ")</span>" if ws else ""} <span class="chip">{esc(k)}</span></span></li>' for d, t, k, ws in CAL) + '</ul>' if CAL else '<p class="hint">No dated events in the next 14 days.</p>'

    # --- mail
    mrows = ''.join(
        f'<tr><td class="mono">{esc(r["date"])}</td><td>{esc(r["source"])}</td><td>{esc(r["kind"])}</td><td class="w">{esc(r["subject"])}<span class="hint">{esc(r["summary"])}</span></td>'
        f'<td>{"<span class=alert>&#9888; " + esc(r["action"]) + "</span>" if r["action"] != "none" else "<span class=hint>none</span>"}{"<span class=hint>by " + esc(r["deadline"]) + "</span>" if r["deadline"] else ""}</td></tr>' for r in M)
    mail_html = (f'<div class="tw"><table><thead><tr><th>Date</th><th>From</th><th>Kind</th><th>What</th><th>Action</th></tr></thead><tbody>{mrows}</tbody></table></div>') if M else '<p class="hint">No mail events logged in the last 30 days.</p>'

    # --- freshness
    fr = ''.join(f'<tr><td>{esc(n)}</td><td class="mono">{esc(d.isoformat()) if d else "-"}</td><td class="r mono">{a if a is not None else "-"}</td>'
                 f'<td>{"<span class=alert>&#9888; stale</span>" if a is not None and a > STALE_DAYS else "ok"}</td></tr>' for n, d, a in F)
    fr_html = f'<div class="tw"><table><thead><tr><th>Source</th><th>Valuation date</th><th class="r">Age (days)</th><th>Status</th></tr></thead><tbody>{fr}</tbody></table></div>'

    banner = '<div class="card" style="border-left:4px solid var(--warn,#b7791f)"><b>DEMO DATA</b> &mdash; synthetic holdings, news and sources (example.com). Nothing here is real or advice. Run the <code>setup</code> skill to use your own exports.</div>' if DEMO else ''
    body = f'''<header><h1>Daily dashboard</h1><div class="meta">{esc(TODAY)} &middot; own total {money(tot)} {BASE} (incl. cash) &middot; not financial advice</div></header>{banner}
<nav class="bar" aria-label="Sections"><a href="#attention">Attention</a><a href="#signals">Signals</a><a href="#positions">Positions</a><a href="#outlook">Top-15 outlook</a><a href="#calendar">Calendar</a><a href="#mail">Mail</a><a href="#data">Data</a></nav>
<div class="stats">{tiles_html}</div>
<section class="card" id="attention"><h2>Needs attention</h2><p class="sub">Alerts, mail that asks for action, non-neutral outlook calls, events within a day, stale data</p>{att_html}</section>
<section class="card" id="signals"><h2>Signals touching the portfolio</h2><p class="sub">Scenario {BASE} = exposure x assumed price move; ranges are assumptions. Open a row for positions and action candidates.</p>
<div class="row"><div class="seg" id="sigf" role="group" aria-label="Signal filter"><button data-f="all" aria-pressed="true">All ({len(S)})</button><button data-f="alert" aria-pressed="false">Alerts ({len(alerts)})</button></div></div>{sig_html}</section>
<section class="card" id="positions"><h2>Affected positions</h2><p class="sub">Per position: signals touching it and the summed scenario range (signals overlap, so the sum overstates a net effect).</p>
<div class="row"><div class="seg" id="posf" role="group" aria-label="Position filter"><button data-f="all" aria-pressed="true">All</button><button data-f="alert" aria-pressed="false">With alerts</button><button data-f="down" aria-pressed="false">Outlook down</button><button data-f="up" aria-pressed="false">Outlook up</button></div>
<input type="search" id="q" placeholder="Filter positions" aria-label="Filter positions"><span class="hint" id="pcount"></span></div>{pos_html}</section>
<section class="card" id="outlook"><h2>Top-15 outlook, next {pb.get("outlook", {}).get("horizon_days", 28)} days</h2><p class="sub">News, company news and press releases per holding, scored from sourced drivers. Evidence = number of sourced drivers and distinct domains, not odds.</p>{out_html}</section>
<section class="card" id="calendar"><h2>Next 14 days</h2><p class="sub">Dated catalysts from the outlook, signals and mail deadlines</p>{cal_html}</section>
<section class="card" id="mail"><h2>Mail events, last 30 days</h2><p class="sub">Routes configured in config/sources.yaml (ingest-email)</p>{mail_html}</section>
<section class="card" id="data"><h2>Data freshness</h2><p class="sub">Valuation date of each platform index; older than {STALE_DAYS} days is flagged</p>{fr_html}</section>
<footer>Generated {esc(TODAY)} by scripts/build_dashboard_html.py. Leans and scenario ranges are tilts from dated sources and assumptions. Not financial advice.</footer>'''

    script = r'''
function seg(id,fn){const g=document.getElementById(id);if(!g)return;g.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));fn(b.dataset.f)})}
let sf='all',pf='all';
function sigs(){document.querySelectorAll('#signals details.it').forEach(d=>{d.hidden=sf==='alert'&&d.dataset.alert!=='1'})}
function pos(){const t=document.getElementById('tpos');if(!t)return;const q=document.getElementById('q').value.toLowerCase();let n=0;
 t.tBodies[0].querySelectorAll('tr').forEach(r=>{const ok=(pf==='all'||(pf==='alert'&&r.dataset.alert==='1')||r.dataset.lean===pf)&&(!q||r.cells[0].textContent.toLowerCase().includes(q));r.hidden=!ok;if(ok)n++});
 document.getElementById('pcount').textContent=n+' of '+t.tBodies[0].rows.length}
seg('sigf',f=>{sf=f;sigs()});seg('posf',f=>{pf=f;pos()});
const qq=document.getElementById('q');if(qq)qq.addEventListener('input',pos);
const tp=document.getElementById('tpos');
if(tp){let dir={};tp.tHead.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const c=+b.dataset.c;dir[c]=-(dir[c]||(c===0||c===6?-1:1));
 const rows=[...tp.tBodies[0].rows];rows.sort((a,z)=>{const x=a.cells[c].dataset.v,y=z.cells[c].dataset.v;const nx=parseFloat(x),ny=parseFloat(y);
  const r=(isNaN(nx)||isNaN(ny))?String(x).localeCompare(String(y)):nx-ny;return r*dir[c]});rows.forEach(r=>tp.tBodies[0].appendChild(r));
 tp.tHead.querySelectorAll('th').forEach((th,i)=>th.setAttribute('aria-sort',i===c?(dir[c]>0?'ascending':'descending'):'none'))})}
pos();
'''
    return H.fragment('Daily Dashboard', body, script), dict(alerts=len(alerts), signals=len(S), touched_pct=touched_v / tot * 100, up=n_up, down=n_dn, neutral=n_ne, mail=len(M), stale=len(stale))


def main():
    frag, info = build()
    d = f'data/reports/{TODAY}'
    os.makedirs(d, exist_ok=True)
    open(f'{d}/dashboard.artifact.html', 'w', encoding='utf-8').write(frag)
    open(f'{d}/dashboard.html', 'w', encoding='utf-8').write(H.standalone(frag))
    print(f'dashboard -> {d}/dashboard.html (+ .artifact.html), {len(frag) // 1024} KB', json.dumps(info))


if __name__ == '__main__':
    main()

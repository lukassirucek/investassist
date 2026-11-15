#!/usr/bin/env python3
"""Status e-mail: builds the body of the "[Investassist] Status - YYYYMMDD" e-mail (session summary, updated totals, changes, alerts, data gaps) and manages the opt-in.
Rule: RULES.md section G. Skill: `send-status-email`. The e-mail itself is sent by the agent with a mail connector (this script has no network access).

Usage:
  python3 -I scripts/status_email.py check                              exit 0 + prints the recipient if status e-mails are enabled AND confirmed twice; exit 1 otherwise (then do not send)
  python3 -I scripts/status_email.py enable --to ADDR --confirmed       opt in (config/alerts.yaml `status_email`). Only after the user typed the address AND confirmed it a second time (setup skill)
  python3 -I scripts/status_email.py disable                            opt out
  python3 -I scripts/status_email.py build [YYYY-MM-DD] [--summary-file F]   write data/publish/status_email_<YYYYMMDD>.txt (+ .subject) and print the subject; privacy scan inside, exit 1 if it fails
  python3 -I scripts/status_email.py sent [YYYY-MM-DD]                  after sending: store today's per-platform totals as the baseline for the next "change since" line and log it
Inputs : data/index/master.positions.csv (+ marks), data/reports/<day>/daily_digest.md, data/fx/fx_latest.csv, data/publish/registry.csv (Drive folder), the summary file written by the agent
         (what was done in the session: 3-10 plain lines, no account numbers).
Outputs: data/publish/status_email_<YYYYMMDD>.txt, .subject; data/publish/status_snapshots.csv (date,platform,value_base); a line in data/portfolio/ingest_log.md.
Config : config/alerts.yaml -> status_email: {enabled, to, confirmed, confirmed_at, subject}. Default is OFF: nothing is ever sent without the double confirmation.
The e-mail contains sensitive totals, never account numbers beyond the last 4 digits, IBANs or credentials (privacy scan from drive_publish_bundle.py).
"""
import csv, datetime as dt, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_publish_bundle as B
from common import OWNER

CFG = 'config/alerts.yaml'
PUB = 'data/publish'
MAIL = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
SUBJ = '[Investassist] Status - {YYYYMMDD}'


def cfg():
    """Minimal reader for the `status_email:` block (no PyYAML dependency)."""
    d = {}
    if not os.path.exists(CFG):
        return d
    on = False
    for ln in open(CFG, encoding='utf-8'):
        if re.match(r'^status_email:\s*(#.*)?$', ln):
            on = True
            continue
        if on:
            if ln.strip() and not ln.startswith((' ', '\t')):
                break
            m = re.match(r'^\s+(\w+):\s*(.*?)\s*(#.*)?$', ln)
            if m:
                d[m.group(1)] = m.group(2).strip().strip('"')
    return d


def write_cfg(vals):
    txt = open(CFG, encoding='utf-8').read() if os.path.exists(CFG) else ''
    txt = re.sub(r'\nstatus_email:[^\n]*\n(?:[ \t]+.*\n?)*', '\n', txt).rstrip('\n') + '\n'
    block = ('\nstatus_email:   # RULES.md G; opt-in, needs the address typed and confirmed twice (setup skill). Subject date = today, YYYYMMDD.\n'
             f'  enabled: {str(vals["enabled"]).lower()}\n  to: "{vals["to"]}"\n  confirmed: {str(vals["confirmed"]).lower()}\n  confirmed_at: "{vals["confirmed_at"]}"\n'
             f'  subject: "{vals.get("subject", SUBJ)}"\n')
    open(CFG, 'w', encoding='utf-8').write(txt + block)


def check():
    c = cfg()
    ok = c.get('enabled') == 'true' and c.get('confirmed') == 'true' and MAIL.match(c.get('to', '') or '')
    if not ok:
        print('status e-mail: not enabled/confirmed - do not send')
        sys.exit(1)
    print(c['to'])


def subject(day):
    return cfg().get('subject', SUBJ).replace('{YYYYMMDD}', day.replace('-', ''))


def snapshots():
    p = f'{PUB}/status_snapshots.csv'
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def build(day, summary_file):
    master = 'data/index/master.positions.csv'
    rows = list(csv.DictReader(open(master, encoding='utf-8')))
    own, cls, ccy, dates, oth = {}, {}, {}, {}, {}
    for r in rows:
        if r.get('status') in ('sold_out', 'converted', 'repaid') or not r.get('value_base'):
            continue
        v, o = float(r['value_base']), (r.get('owner') or '').strip()
        if o in ('', OWNER):
            own[r['platform']] = own.get(r['platform'], 0) + v
            cls[r['asset_class']] = cls.get(r['asset_class'], 0) + v
            ccy[r['report_ccy']] = ccy.get(r['report_ccy'], 0) + v
            if r['asset_class'] != 'other' or r['platform'] not in dates:
                dates[r['platform']] = max(dates.get(r['platform'], ''), r.get('valuation_date', ''))
        else:
            oth[o] = oth.get(o, 0) + v
    tot = sum(own.values())
    snaps = snapshots()
    prev_days = sorted({s['date'] for s in snaps if s['date'] < day})
    prev = {s['platform']: float(s['value_base']) for s in snaps if prev_days and s['date'] == prev_days[-1]}
    fxd = max((r['date'] for r in csv.DictReader(open('data/fx/fx_latest.csv'))), default='') if os.path.exists('data/fx/fx_latest.csv') else ''
    summ = B.rd(summary_file).strip() if summary_file else '(no session summary was provided)'
    L = [f'Investassist status {day}', '', 'WHAT WE DID', summ, '', 'OWN TOTAL']
    L.append(f'{tot:,.0f} CZK  (positions as of {max(dates.values()) if dates else "?"}, FX as of {fxd})')
    if prev:
        pt = sum(prev.values())
        L.append(f'Change since {prev_days[-1]}: {tot - pt:+,.0f} CZK ({100 * (tot - pt) / pt:+.2f} %)  [mixes market moves, flows and newly tracked accounts]')
    else:
        L.append('Change since last status: n/a (first status e-mail)')
    L += ['', 'BY PLATFORM (CZK, share, change since last status, valuation date)']
    for k, v in sorted(own.items(), key=lambda a: -a[1]):
        d = f'{v - prev[k]:+,.0f}' if k in prev else 'new'
        L.append(f'  {k:<16}{v:>14,.0f}  {100 * v / tot:5.1f} %  {d:>10}  {dates.get(k, "")}')
    L += ['', 'BY ASSET CLASS (CZK)'] + [f'  {k:<16}{v:>14,.0f}  {100 * v / tot:5.1f} %' for k, v in sorted(cls.items(), key=lambda a: -a[1]) if abs(v) >= 1]
    L += ['', 'BY CURRENCY (CZK)'] + [f'  {k:<16}{v:>14,.0f}  {100 * v / tot:5.1f} %' for k, v in sorted(ccy.items(), key=lambda a: -a[1])]
    if oth:
        L += ['', 'OTHER OWNERS (not in own total)'] + [f'  {k}: {v:,.0f} CZK' for k, v in sorted(oth.items())]
    dg = f'data/reports/{day}/daily_digest.md'
    dg = dg if os.path.exists(dg) else B.newest('data/reports/*/daily_digest.md')
    if dg:
        t = B.rd(dg)
        m = re.search(r'active signals (\d+) \| alerts (\d+)', t)
        heads = re.findall(r'^### (\[[^\]]+\] .+)$', t.split('## ALERTS', 1)[-1], re.M)[:5]
        L += ['', f'ALERTS ({m.group(2) if m else "?"} active, {m.group(1) if m else "?"} signals; digest {os.path.basename(os.path.dirname(dg))})'] + [f'  - {h[:150]}' for h in heads]
    stale = sorted(k for k, d in dates.items() if d and (dt.date.fromisoformat(day) - dt.date.fromisoformat(d)).days > 14)
    marks = [r for r in rows if r['platform'] == 'marks' or r.get('account') == 'Valuation mark since statement']
    L += ['', 'DATA QUALITY']
    L.append(f'  platforms whose position-level data is older than 14 days (the total may be newer via a mark): {", ".join(stale) if stale else "none"}')
    L.append(f'  valuation marks (app total newer than the statement, INFERENCE): {len(marks)}; position-level exposure for those platforms is as of the statement')
    reg = {r['name']: r for r in csv.DictReader(open(f'{PUB}/registry.csv', encoding='utf-8'))} if os.path.exists(f'{PUB}/registry.csv') else {}
    if reg.get('_folder'):
        L += ['', 'DRIVE (indexes, summaries, dashboard)', f'  https://drive.google.com/drive/folders/{reg["_folder"]["drive_id"]}']
    L += ['', 'Sensitive: contains portfolio totals. Signals and scenarios are for review, not financial advice. Sent by the Investassist agent (RULES.md G).']
    body = '\n'.join(L) + '\n'
    bad = [lab for rx, lab in ((B.IBAN, 'IBAN-like'), (B.ACCT, 'account/bank-code'), (B.LONG, '10+ digit run')) if rx.search(body)]
    deny = [t.strip().lower() for t in B.rd('local/publish_denylist.txt').splitlines() if t.strip() and not t.startswith('#')]
    bad += [f'deny-list term' for t in deny if t in body.lower()]
    if bad:
        sys.exit('PRIVACY SCAN FAILED, do not send: ' + ', '.join(bad))
    os.makedirs(PUB, exist_ok=True)
    stem = f'{PUB}/status_email_{day.replace("-", "")}'
    open(stem + '.txt', 'w', encoding='utf-8').write(body)
    open(stem + '.subject', 'w', encoding='utf-8').write(subject(day) + '\n')
    print(subject(day))


def sent(day):
    master = 'data/index/master.positions.csv'
    own = B.own_totals(master)
    keep = [s for s in snapshots() if s['date'] != day]
    keep += [dict(date=day, platform=k, value_base=f'{v:.2f}') for k, v in own.items()]
    with open(f'{PUB}/status_snapshots.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'platform', 'value_base']); w.writeheader(); w.writerows(keep)
    with open('data/portfolio/ingest_log.md', 'a', encoding='utf-8') as f:
        f.write(f'- {day} status e-mail sent to {cfg().get("to", "?")}: "{subject(day)}"; own total {sum(own.values()):,.0f} CZK\n')
    print('baseline stored; logged')


if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a[0] if a else ''
    today = dt.date.today().isoformat()
    day = next((x for x in a[1:] if re.match(r'^\d{4}-\d{2}-\d{2}$', x)), today)
    if cmd == 'check':
        check()
    elif cmd == 'enable':
        to = a[a.index('--to') + 1] if '--to' in a else ''
        if not MAIL.match(to):
            sys.exit('invalid address')
        if '--confirmed' not in a:
            sys.exit('refused: enable only after the user typed the address and confirmed it a second time (--confirmed)')
        write_cfg(dict(enabled=True, to=to, confirmed=True, confirmed_at=dt.datetime.now().isoformat(timespec='minutes')))
        print(f'status e-mails enabled for {to}')
    elif cmd == 'disable':
        c = cfg()
        write_cfg(dict(enabled=False, to=c.get('to', ''), confirmed=False, confirmed_at=''))
        print('status e-mails disabled')
    elif cmd == 'build':
        build(day, a[a.index('--summary-file') + 1] if '--summary-file' in a else None)
    elif cmd == 'sent':
        sent(day)
    else:
        sys.exit(__doc__)

#!/usr/bin/env python3
"""Drive publish bundle: collect the current indexes, summaries and dashboard into data/publish/ so they can be uploaded to the Google Drive publish folder
(readable in Drive and Gemini). Rule: RULES.md section F. Procedure: skill `publish-to-drive`.

Usage:
  python3 -I scripts/drive_publish_bundle.py build [YYYY-MM-DD]   build data/publish/*, run the privacy scan, write MANIFEST.csv; exit 1 if the scan fails (nothing to upload then)
  python3 -I scripts/drive_publish_bundle.py status [--json]      compare MANIFEST.csv with registry.csv: which files are new / changed / same (upload only new + changed)
  python3 -I scripts/drive_publish_bundle.py record NAME DRIVE_ID  store the Drive file id of NAME (after upload) with the current sha256; `record _folder FOLDER_ID` stores the publish folder
Inputs : data/index/*.index.md + master.positions.csv, data/exposure/*.csv|md, data/outlook/top15.csv, data/reports/<day>/{daily_digest.md,dashboard.artifact.html},
         newest file of reports/weekly and reports/alerts, data/fx/fx_latest.csv. Optional deny-list: local/publish_denylist.txt (one forbidden term per line, e.g. a sensitive name).
Outputs: data/publish/<NAME>.<ext> (stable names), data/publish/MANIFEST.csv (name,file,mime,bytes,sha256,as_of,built), data/publish/registry.csv (name,drive_id,sha256,pushed_at).
Privacy: the scan blocks IBANs, account numbers with a bank code (123456789/0800), bare digit runs of 10+ and deny-list terms. Platform *.partial.* indexes are never published.
The master includes other owners' rows (owner column); the README file says so. No network, no Drive access here: the upload itself is done by the agent (skill).
"""
import csv, datetime as dt, glob, hashlib, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OWNER

PUB = 'data/publish'
IBAN = re.compile(r'\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b')
ACCT = re.compile(r'\b\d{2,6}-?\d{6,10}/\d{4}\b')
LONG = re.compile(r'(?<![\w.,/#:-])\d{10,}(?![\w.,])')  # not ISINs (letters), ids in URLs or decimals


def rd(p):
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''


def newest(pattern):
    f = sorted(glob.glob(pattern))
    return f[-1] if f else None


def own_totals(master):
    tot, n = {}, 0
    for r in csv.DictReader(open(master, encoding='utf-8')):
        if r.get('status') in ('sold_out', 'converted', 'repaid') or not r.get('value_base'):
            continue
        if (r.get('owner') or '').strip() in ('', OWNER):
            tot[r['platform']] = tot.get(r['platform'], 0) + float(r['value_base'])
    return tot


def table(path, label, limit=30):
    if not os.path.exists(path):
        return ''
    rows = list(csv.DictReader(open(path, encoding='utf-8')))[:limit]
    if not rows:
        return ''
    keys = list(rows[0])
    s = f'\n### {label}\n\n| ' + ' | '.join(keys) + ' |\n|' + '---|' * len(keys) + '\n'
    return s + ''.join('| ' + ' | '.join(r[k] for k in keys) + ' |\n' for r in rows)


def build(day):
    os.makedirs(PUB, exist_ok=True)
    built = dt.datetime.now().isoformat(timespec='minutes')
    master = 'data/index/master.positions.csv'
    if not os.path.exists(master):
        sys.exit('no master index: run scripts/build_master_index.py first')
    fxd = ''
    if os.path.exists('data/fx/fx_latest.csv'):
        fxd = max(r['date'] for r in csv.DictReader(open('data/fx/fx_latest.csv')))
    mrows = list(csv.DictReader(open(master, encoding='utf-8')))
    asof = max(r['valuation_date'] for r in mrows if r.get('valuation_date'))
    own = own_totals(master)
    own_total = sum(own.values())
    exp_total = sum(float(r['value_base']) for r in csv.DictReader(open('data/exposure/exposure_platform.csv'))) if os.path.exists('data/exposure/exposure_platform.csv') else None
    out = {}  # name -> (ext, mime, text-or-path, source)

    out['01_master_positions'] = ('csv', 'text/csv', None, master)
    out['02_master_index'] = ('md', 'text/plain', None, 'data/index/master.index.md')
    parts = ['# Platform indexes (all platforms, one file)\n\nEach block is the `<platform>.index.md` of one platform. Positions in `<platform>.positions.csv` are summarised there.\n']
    for f in sorted(glob.glob('data/index/*.index.md')):
        if 'master' in f or '.partial.' in f:
            continue
        parts.append(f'\n\n---\n<!-- {os.path.basename(f)} -->\n' + rd(f))
    out['03_platform_indexes'] = ('md', 'text/plain', ''.join(parts), 'data/index/*.index.md')

    s = [f'# Dashboard summary (text companion of the HTML dashboard)\n\nBuilt {built[:10]}. Positions as of {asof}; FX as of {fxd}. Base currency CZK. Own portfolio only (daughters and the business account are excluded).\n']
    s.append(f'\n## Own total\n\n- Master index own total: **{own_total:,.0f} CZK**')
    if exp_total is not None:
        s.append(f'- Exposure map total: {exp_total:,.0f} CZK (statement-based positions). Difference {own_total - exp_total:+,.0f} CZK = valuation marks (app totals newer than statements; position-level exposure for those platforms is stale).')
    s.append('\n## Own total by platform (CZK)\n\n| platform | value | % |\n|---|---:|---:|')
    for k, v in sorted(own.items(), key=lambda a: -a[1]):
        s.append(f'| {k} | {v:,.0f} | {100 * v / own_total:.1f} |')
    s.append('')
    for f, lab in (('class', 'By asset class'), ('currency', 'By currency'), ('sector', 'By sector'), ('hq_country', 'By HQ country'), ('raw_material_touching', 'Raw-material touching'), ('theme_touching', 'Theme touching')):
        s.append(table(f'data/exposure/exposure_{f}.csv', lab, 15))
    if os.path.exists('data/outlook/top15.csv'):
        s.append('\n### Top 15 instruments\n\n| rank | instrument | class | CZK | % | platforms |\n|---|---|---|---:|---:|---|')
        for r in list(csv.DictReader(open('data/outlook/top15.csv', encoding='utf-8')))[:15]:
            s.append(f"| {r['rank']} | {r['instrument']} | {r['cls']} | {float(r['value_base']):,.0f} | {r['pct_total']} | {r['platforms']} |")
    s.append('\n\n## Exposure map\n\n' + rd('data/exposure/exposure_map.md'))
    out['04_dashboard_summary'] = ('md', 'text/plain', '\n'.join(s) + '\n', 'master + exposure + outlook')

    dg = f'data/reports/{day}/daily_digest.md'
    if not os.path.exists(dg):
        dg = newest('data/reports/*/daily_digest.md')
    if dg:
        out['05_daily_digest'] = ('md', 'text/plain', None, dg)
    for sub in ('weekly', 'alerts'):
        n = newest(f'reports/{sub}/*.md')
        if n:
            out[f'07_latest_{sub}'] = ('md', 'text/plain', None, n)
    ah = f'data/reports/{day}/dashboard.artifact.html'
    if not os.path.exists(ah):
        ah = newest('data/reports/*/dashboard.artifact.html')
    if ah:
        out['08_dashboard'] = ('html', 'text/html', None, ah)

    readme = f"""# Investassist published files (README)

Built {built[:10]} by `scripts/drive_publish_bundle.py`. Positions as of {asof}; FX as of {fxd}. Base currency CZK. Do not edit these files in Drive: they are overwritten on every publish (edit the repo, not the copy).

| File | What it is |
|---|---|
| 00_README | this file: what, when, caveats |
| 01_master_positions | every position of every platform, one row each (Sheet). Columns `value_base`/`cost_base` are in CZK. Filter `owner` blank or {OWNER} = own; other owners are listed separately |
| 02_master_index | totals by owner, platform, asset class and currency |
| 03_platform_indexes | per-platform index summaries (source, date, reconciliation notes) |
| 04_dashboard_summary | text version of the dashboard: own total, by platform / class / currency / sector, top 15, exposure map (for Gemini; HTML is not rendered there) |
| 05_daily_digest | signals and alerts matched against the exposure, with FACT / INFERENCE labels |
| 07_latest_weekly, 07_latest_alerts | newest weekly report / alert file, if any |
| 08_dashboard | interactive HTML dashboard (open in a browser; Gemini cannot render it, use 04) |

Caveats: own total {own_total:,.0f} CZK. The master contains other owners' accounts (e.g. children, a business) in the `owner` column (reported separately, excluded from own totals). Platforms with only an app total newer than the last statement carry a `valuation mark` row (INFERENCE); their position-level exposure is as of the statement. Credit-card used amounts are negative `loan_liability` rows. Account numbers are masked to the last 4 digits; no credentials or IBANs are published. Signals and scenarios are for review, not financial advice.
"""
    out['00_README'] = ('md', 'text/plain', readme, 'generated')

    bad, man = [], []
    deny = [t.strip().lower() for t in rd('local/publish_denylist.txt').splitlines() if t.strip() and not t.startswith('#')]
    for name, (ext, mime, text, src) in sorted(out.items()):
        dst = f'{PUB}/{name}.{ext}'
        if text is not None and not os.path.exists(text):
            open(dst, 'w', encoding='utf-8').write(text)   # generated text
        else:
            shutil.copyfile(text or src, dst)              # text is a path (01) or None (copy of src)
        body = rd(dst)
        for rx, lab in ((IBAN, 'IBAN-like'), (ACCT, 'account/bank-code'), (LONG, '10+ digit run')):
            if ext == 'html' and rx is LONG:
                continue
            m = rx.search(body)
            if m:
                bad.append(f'{name}: {lab}: {m.group(0)[:6]}...')
        for t in deny:
            if t in body.lower():
                bad.append(f'{name}: deny-list term "{t[:3]}..."')
        raw = open(dst, 'rb').read()
        man.append(dict(name=name, file=os.path.basename(dst), mime=mime, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), as_of=asof, built=built))
    with open(f'{PUB}/MANIFEST.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(man[0])); w.writeheader(); w.writerows(man)
    if bad:
        print('PRIVACY SCAN FAILED - do not upload:\n  ' + '\n  '.join(bad))
        sys.exit(1)
    print(f'built {len(man)} files in {PUB}/ (as of {asof}); privacy scan clean')


def registry():
    p = f'{PUB}/registry.csv'
    return {r['name']: r for r in csv.DictReader(open(p, encoding='utf-8'))} if os.path.exists(p) else {}


def save_registry(reg):
    with open(f'{PUB}/registry.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'drive_id', 'sha256', 'pushed_at']); w.writeheader(); w.writerows(reg.values())


def status(as_json):
    reg = registry()
    res = []
    for m in csv.DictReader(open(f'{PUB}/MANIFEST.csv', encoding='utf-8')):
        r = reg.get(m['name'])
        st = 'new' if not r else ('same' if r['sha256'] == m['sha256'] else 'changed')
        res.append(dict(name=m['name'], file=m['file'], mime=m['mime'], bytes=m['bytes'], sha256=m['sha256'], state=st, drive_id=(r or {}).get('drive_id', '')))
    folder = reg.get('_folder', {}).get('drive_id', '')
    if as_json:
        print(json.dumps(dict(folder_id=folder, files=res), indent=1))
    else:
        print(f'publish folder id: {folder or "(not set)"}')
        for r in res:
            print(f"{r['state']:8} {r['file']:34} {r['bytes']:>9} B  {r['drive_id']}")


def record(name, drive_id):
    reg = registry()
    sha = ''
    if name != '_folder':
        sha = next(m['sha256'] for m in csv.DictReader(open(f'{PUB}/MANIFEST.csv', encoding='utf-8')) if m['name'] == name)
    reg[name] = dict(name=name, drive_id=drive_id, sha256=sha, pushed_at=dt.datetime.now().isoformat(timespec='minutes'))
    save_registry(reg)
    print(f'recorded {name} -> {drive_id}')


if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a[0] if a else 'build'
    if cmd == 'build':
        build(a[1] if len(a) > 1 else dt.date.today().isoformat())
    elif cmd == 'status':
        status('--json' in a)
    elif cmd == 'record' and len(a) == 3:
        record(a[1], a[2])
    else:
        sys.exit(__doc__)

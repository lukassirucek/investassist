#!/usr/bin/env python3
"""Raiffeisenbank (Czech Republic) "Investice" statement PDFs ("Výpis z majetkového účtu") -> data/index/raiffeisen.positions.csv + raiffeisen.index.md

Usage: python3 -I parsers/raiffeisen_index.py <statement.pdf> [<statement2.pdf> ...] [--out data/index] [--dip CONTRACT ...]
         [--cash CONTRACT=AMOUNT ...] [--cash-date YYYY-MM-DD] [--owner NAME]
Needs `pdftotext` (poppler-utils). One PDF = one contract (one account). Statement lists positions only: NO purchase prices or dates, so cost and P&L stay blank.
  --dip CONTRACT   contract number(s) that are DIP (long-term investment product); also detected when the file name contains "dip". Others are `regular`.
  --cash C=AMOUNT  available cash per contract as you read it in the app (the statement has none); written as a cash row valued at --cash-date (default today).
Values: the statement's own "Objem v měně portfolia" (CZK, with the statement FX for EUR/USD instruments) at the statement's position date.
Every row is checked: units x price = total in instrument currency, and total x FX = value in portfolio currency; the sum is checked against the statement total.
"""
import argparse, csv, datetime as dt, os, re, subprocess, sys
from collections import defaultdict

COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']
NUM = r'(?:-?\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?)'
ROW = re.compile(r'^(?P<isin>[A-Z]{2}[A-Z0-9]{9,11})\s+(?P<name>.*?)\s{2,}(?P<units>%s)\s+(?P<ccy>[A-Z]{3})\s+(?P<price>%s)\s+(?P=ccy)\s+(?P<total>%s)\s+(?P=ccy)\s+(?P<fx>%s)\s+(?P<val>%s)\s+(?P<pccy>[A-Z]{3})\s*$' % (NUM, NUM, NUM, NUM, NUM))
ETF_HINT = re.compile(r'\bETF\b|\bETC\b|UCITS', re.I)
FUND_HINT = re.compile(r'\bFund|Funds\b|S&P500 - C|Fond\b', re.I)


def num(s):
    return float(re.sub(r'[\s  ]', '', s).replace(',', '.'))


def cz_date(s):
    d, m, y = [int(x) for x in re.findall(r'\d+', s)[:3]]
    return dt.date(y, m, d).isoformat()


def parse(path):
    try:
        text = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f'pdftotext failed for {path} ({e}); install poppler-utils')
    if 'VÝPIS Z MAJETKOVÉHO ÚČTU' not in text:
        sys.exit(f'{os.path.basename(path)}: not a Raiffeisen "Výpis z majetkového účtu"')
    g = lambda label: (re.search(label + r'\s+(.+)', text) or [None, ''])[1].strip()
    H = dict(no=g('Číslo výpisu'), typ=g('Typ výpisu'), pos=cz_date(g('Datum pozice')), issued=cz_date(g('Datum vystavení')), contract=g('Identifikace smlouvy'))
    lines = text.splitlines()
    ent, cur = [], None
    start = next(i for i, l in enumerate(lines) if l.startswith('ISIN'))
    for l in lines[start:]:
        if l.startswith('Celkový objem portfolia'):
            m = re.search(r'(%s)\s+([A-Z]{3})\s*$' % NUM, l)
            H.setdefault('totals', []).append(num(m.group(1))) if m else None
            cur = None; continue
        if not l.strip() or l.startswith(('ISIN', 'Neobdržíme')):
            continue
        if 'PRÁZDNÉ PORTOFOLIO' in l or l.startswith('PORTFOLIO'):
            cur = None; continue
        m = ROW.match(l.rstrip())
        if m:
            cur = dict(m.groupdict()); cur['name'] = [cur['name'].strip()]; cur['nominal'] = ''; ent.append(cur); continue
        if re.match(r'^[A-Z]{2}[A-Z0-9]{9,11}\s', l):   # an ISIN line that did not match the numeric tail: surface it, never skip silently
            ent.append(dict(isin=l.split()[0], bad=l.strip())); cur = None; continue
        if cur is None or 'bad' in cur:
            continue
        s = l.rstrip()
        if re.match(r'^\S\s{3,}', s) and len(cur['isin']) < 12 and re.match(r'^\d|^[A-Z0-9]$', s[0]):    # ISIN wrapped onto the next line: "5     ý certifikát"
            cur['isin'] += s[0]; s = s[1:]
        parts = [p for p in re.split(r'\s{3,}', s.strip()) if p]
        for p in parts:
            if re.fullmatch(NUM, p):
                cur['nominal'] = p.strip()
            elif p:
                if cur['name'] and re.match(r'^[a-zà-ž]\s', p) and cur['name'][-1][-1:].isalpha():
                    cur['name'][-1] += p              # word split across lines: "Garantovan" + "ý certifikát"
                else:
                    cur['name'].append(p)
    for e in ent:
        if 'name' in e:
            e['name'] = ' '.join(e['name'])
    return H, ent


def klass(e):
    if ETF_HINT.search(e['name']):
        return 'etf'
    if FUND_HINT.search(e['name']):
        return 'fund'
    if re.search(r'certifik', e['name'], re.I):
        return 'structured_certificate'
    return 'stock'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdfs', nargs='+'); ap.add_argument('--out', default='data/index'); ap.add_argument('--dip', action='append', default=[])
    ap.add_argument('--cash', action='append', default=[]); ap.add_argument('--cash-date', default=dt.date.today().isoformat()); ap.add_argument('--owner', default='')
    a = ap.parse_args()
    cash = dict(c.split('=', 1) for c in a.cash)
    rows, checks, sums, per = [], [], defaultdict(float), []
    for path in a.pdfs:
        H, ent = parse(path)
        ptype = 'dip' if (H['contract'] in a.dip or 'dip' in os.path.basename(path).lower()) else 'regular'
        acct = f"Raiffeisen investice - contract ...{H['contract'][-3:]}"
        for e in ent:
            if 'bad' in e:
                checks.append((f"{H['contract']}: line not understood, row skipped: {e['bad'][:60]}", False)); continue
            u, px, tn, fx, v = num(e['units']), num(e['price']), num(e['total']), num(e['fx']), num(e['val'])
            ok = abs(u * px - tn) <= 0.02 + 0.001 * tn and abs(tn * fx - v) <= 0.05 + 0.0005 * v
            checks.append((f"{H['contract']} {e['name'][:28]}: units x price = total; total x FX = value", ok))
            sums[H['contract']] += v
            rows.append(dict(platform='raiffeisen', account=acct, portfolio_type=ptype, asset_class=klass(e), instrument_id=e['isin'], name=e['name'], country='CZ' if e['isin'].startswith('CZ') else '',
                             status='held', native_ccy=e['ccy'], units_net=f'{u:g}', report_ccy=e['pccy'], value=f'{v:.2f}', price=f'{px:g}', price_ccy=e['ccy'], valuation_date=H['pos'], confidence='high',
                             notes=f"statement {H['no']} position date {H['pos']}; native value {tn:g} {e['ccy']}, FX {fx:g}; nominal {e['nominal'] or '-'}; cost not on statement", owner=a.owner))
        tot = H.get('totals', [None])[0]
        if tot is not None:
            checks.append((f"{H['contract']}: sum of positions {sums[H['contract']]:,.2f} = statement total {tot:,.2f}", abs(sums[H['contract']] - tot) <= 0.05))
        elif ent:
            checks.append((f"{H['contract']}: statement has no total line; sum computed {sums[H['contract']]:,.2f}", True))
        c = cash.get(H['contract'])
        if c is not None:
            rows.append(dict(platform='raiffeisen', account=acct, portfolio_type=ptype, asset_class='cash', instrument_id='CZK', symbol='CZK', name='Available funds', status='held', native_ccy='CZK',
                             units_net=f'{float(c):.2f}', report_ccy='CZK', value=f'{float(c):.2f}', valuation_date=a.cash_date, confidence='medium', notes=f'stated by owner {a.cash_date}', owner=a.owner))
        per.append((H, ptype, sums[H['contract']], tot, float(c) if c is not None else None))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'raiffeisen.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    vd = max(h['pos'] for h, *_ in per)
    md = [f"---\nplatform: raiffeisen\nprovider: Raiffeisenbank a.s. - Investice (statement 'Výpis z majetkového účtu')\nsource_files: {', '.join(os.path.basename(p) for p in a.pdfs)}\nvaluation_date: {vd}\ngenerated: {dt.date.today().isoformat()}\nreport_ccy: CZK\npositions_csv: raiffeisen.positions.csv\n---\n",
          "# Raiffeisen investice index\n\n| Contract | Type | Position date | Positions (statement) | Statement total | Cash (stated) |\n|---|---|---|---:|---:|---:|\n"]
    for H, pt, s, t, c in per:
        md.append(f"| ...{H['contract'][-3:]} | {pt} | {H['pos']} | {s:,.2f} | {t:,.2f} | {'' if c is None else format(c, ',.2f')} |\n" if t is not None else f"| ...{H['contract'][-3:]} | {pt} | {H['pos']} | {s:,.2f} | - | {'' if c is None else format(c, ',.2f')} |\n")
    md.append("\n## Reconciliation\n" + ''.join(f"- {'OK' if ok else 'MISMATCH'}: {n}\n" for n, ok in checks))
    md.append("\n## Caveats\n- Values are the statement's (prices of the position date), not refreshed. The statement lists no purchase prices or dates: cost basis and P&L are unknown.\n- Foreign-currency instruments are converted with the statement's FX.\n- Cash is not on the statement; it appears only if you pass `--cash`.\n- Overlaps with other platforms (same index funds or companies) are aggregated later by instrument; `portfolio_type` stays separate for tax.\n- Rebuild: `python3 -I parsers/raiffeisen_index.py <statement.pdf>... --out data/index`\n")
    open(os.path.join(a.out, 'raiffeisen.index.md'), 'w', encoding='utf-8').write(''.join(md))
    for n, ok in checks:
        print('OK ' if ok else 'MISMATCH', n)
    print(f'OK raiffeisen: {len(rows)} rows')


if __name__ == '__main__':
    main()

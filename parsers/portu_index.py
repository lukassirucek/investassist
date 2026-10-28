#!/usr/bin/env python3
"""Portu (Czech robo-advisor, WOOD Retail Investments) monthly statements -> data/index/portu.positions.csv + portu.index.md

Usage: python3 -I parsers/portu_index.py <manifest.csv> [--out data/index]
Manifest columns: file,owner,portfolio_type,holder_note   (files are resolved next to the manifest; .pdf is converted with `pdftotext -layout`, .txt is used as is)
  owner: blank = you (the profile owner); another name = a separate person (child, partner), reported separately from your totals
  portfolio_type: regular | dip (DIP = Czech long-term investment product; never merged with regular in tax output)
One statement = one Portu account holding one or more portfolios (one per risk profile). Statement is monthly: units and values only; the statement has no ISIN
(Bloomberg-style ticker + exchange: GY = Xetra, LN = London) and no cost basis. Values are in CZK with the statement's FX for EUR/USD/GBP legs.
"""
import csv, datetime as dt, os, re, subprocess, sys

COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net',
        'units_bought', 'units_sold', 'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross',
        'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend', 'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']
N = r'-?\d[\d\s\u00a0]*,\d+'
NAMES = {
 'XMK9 GY': 'Xtrackers MSCI Japan EUR Hedged UCITS ETF', 'CSPX LN': 'iShares Core S&P 500 UCITS ETF', 'IGLN LN': 'iShares Physical Gold ETC',
 'ZPRS GY': 'SPDR MSCI World Small Cap UCITS', 'SXR7 GY': 'iShares Core MSCI EMU UCITS ETF', '3SUD GY': 'iShares J.P. Morgan USD EM Bond UCITS ETF',
 'HYLA LN': 'iShares Global High Yield Corp Bond UCITS ETF', 'XBLC GY': 'Xtrackers II EUR Corporate Bond UCITS ETF', 'LQDA LN': 'iShares USD Corp Bond UCITS ETF',
 'DPYE LN': 'iShares Developed Markets Property Yield UCITS ETF', 'IGIL LN': 'iShares Global Inflation Linked Govt Bond UCITS ETF',
 'SDIA LN': 'iShares USD Short Duration Corp Bond UCITS ETF', 'IS3N GY': 'iShares Core MSCI EM IMI UCITS ETF', 'DTLA LN': 'iShares USD Treasury Bond 20+y UCITS ETF',
 'AMEA GY': 'Amundi MSCI EM Asia UCITS ETF', 'IUSK GY': 'iShares MSCI Europe SRI UCITS ETF', 'QDVS GY': 'iShares MSCI EM SRI UCITS ETF',
 'CUSS LN': 'iShares MSCI USA Small Cap ESG Enhanced UCITS ETF', 'SUAS LN': 'iShares MSCI USA SRI UCITS ETF', 'XZMJ GY': 'Xtrackers MSCI Japan ESG UCITS ETF 1C',
 'EMSA LN': 'iShares J.P. Morgan Advanced $ EM Bond UCITS ETF', 'DHYA LN': 'iShares $ High Yield Corp Bond ESG UCITS ETF',
 '5UOA GY': 'iShares USD Corp Bond ESG SRI UCITS ETF', 'SUA0 GY': 'iShares EUR Corp Bond ESG SRI UCITS ETF'}

def num(s):
    return float(re.sub(r'[\s\u00a0]', '', s).replace(',', '.'))

def load_text(path):
    if path.lower().endswith('.pdf'):
        try:
            return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as e:
            sys.exit(f'pdftotext failed for {path} ({e}); install poppler-utils or give the .txt')
    return open(path, encoding='utf-8').read()


def parse(path):
    L = load_text(path).splitlines()
    i2 = next(i for i, l in enumerate(L) if l.startswith('II. Z'))
    i3 = next(i for i, l in enumerate(L) if l.startswith('III. Prov'))
    i4 = next((i for i, l in enumerate(L) if l.startswith('IV. Pene') or l.startswith('IV. Pen')), len(L))
    head = '\n'.join(L[:i2])
    kind = 'DIP' if 'DIP' in head[:200] else 'regular'
    period = re.search(r'(\d\d\.\d\d\.\d{4})\s*-\s*(\d\d\.\d\d\.\d{4})', head).groups()
    owner_name = re.search(r'Jméno majitele:\s+(.+)', head).group(1).strip()
    # overview rows
    ov = []
    for l in L[:i2]:
        m = re.search(r'(\d{7,8})\s+CZK\s+(%s)\s+(%s)\s+(\d+,\d+)\s*%%' % (N, N), l)
        if m: ov.append(dict(vs=m.group(1), start=num(m.group(2)), end=num(m.group(3)), yld=num(m.group(4))))
    # balances
    blocks, cur = [], None
    for idx in range(i2, i3):
        l = L[idx]
        if l.strip().startswith('Cenné papíry'):
            k = idx - 1
            while not L[k].strip(): k -= 1
            cur = dict(title=L[k].strip(), rows=[], cash=[], total=None); blocks.append(cur); continue
        if cur is None: continue
        m = re.match(r'^\s*([A-Z0-9]{3,5} (?:GY|LN))\s+.*?\s(EUR|USD|GBP)\s+(%s)\s+(%s)\s+(%s)\s+(%s)\s+(%s)\s*$' % (N, N, N, N, N), l)
        if m:
            cur['rows'].append(dict(sym=m.group(1), ccy=m.group(2), qty=num(m.group(3)), price=num(m.group(4)), val=num(m.group(5)), fx=num(m.group(6)), czk=num(m.group(7)))); continue
        m = re.match(r'^\s*(CZK|EUR|USD)\s+Hotovost\s+(CZK|EUR|USD)\s+(%s)\s+(%s)\s+(%s)\s*$' % (N, N, N), l)
        if m:
            cur['cash'].append(dict(ccy=m.group(2), amt=num(m.group(3)), fx=num(m.group(4)), czk=num(m.group(5)))); continue
        m = re.match(r'^\s*Celkem\s+(%s)\s+CZK' % N, l)
        if m: cur['total'] = num(m.group(1))
    # transactions per block
    titles = [b['title'] for b in blocks]
    tx = {t: dict(deposits=0.0, withdrawals=0.0, trades=0, buys=0, sells=0, fees=0.0, income=0.0, fx=0) for t in titles}
    t_cur, sub = None, None
    for idx in range(i3, i4):
        s = L[idx].strip()
        if s in titles: t_cur, sub = s, None; continue
        if t_cur is None: continue
        for h in ('Vklady', 'Výběry', 'Připsané dividendy a úroky', 'Provedené obchody', 'Forexové obchody', 'Převody', 'Poplatky'):
            if s == h: sub = h
        d = tx[t_cur]
        mt = re.match(r'^\d\d\.\d\d\.\d{4} \d\d:\d\d\s+(Nákup|Prodej)', s) if sub == 'Provedené obchody' else None
        if mt:
            d['trades'] += 1; d['buys' if mt.group(1) == 'Nákup' else 'sells'] += 1
        if sub == 'Forexové obchody' and re.match(r'^\d\d\.\d\d\.\d{4} \d\d:\d\d', s): d['fx'] += 1
        m = re.match(r'^Celkem\s+(%s)\s+CZK' % N, s)
        if m:
            v = num(m.group(1))
            if sub == 'Vklady': d['deposits'] = v
            elif sub == 'Výběry': d['withdrawals'] = v
            elif sub == 'Poplatky': d['fees'] = v
            elif sub == 'Připsané dividendy a úroky': d['income'] = v
    # fee detail (gross / discount)
    fee_gross = {t: 0.0 for t in titles}; fee_disc = {t: 0.0 for t in titles}
    t_cur, sub = None, None
    for idx in range(i3, i4):
        s = L[idx].strip()
        if s in titles: t_cur, sub = s, None; continue
        if s == 'Poplatky': sub = s
        elif s in ('Vklady', 'Výběry', 'Připsané dividendy a úroky', 'Provedené obchody', 'Forexové obchody', 'Převody'): sub = s
        if t_cur and sub == 'Poplatky':
            m = re.match(r'^\d\d\.\d\d\.\d{4}\s+\d\d - \d{4}\s+(Poplatek|Sleva na poplatku)\s+CZK\s+(%s)(?:\s+(%s)\s+(%s))?$' % (N, N, N), s)
            if m:
                v = num(m.group(4) if m.group(4) else m.group(2))
                if m.group(1) == 'Poplatek': fee_gross[t_cur] += v
                else: fee_disc[t_cur] += v
    return dict(kind=kind, period=period, owner_name=owner_name, ov=ov, blocks=blocks, tx=tx, fee_gross=fee_gross, fee_disc=fee_disc)

def main(manifest, out='data/index'):
    base = os.path.dirname(os.path.abspath(manifest))
    M = list(csv.DictReader(open(manifest, encoding='utf-8')))
    rows, checks, sect = [], [], []
    for m in M:
        P = parse(os.path.join(base, m['file']))
        asof = dt.datetime.strptime(P['period'][1], '%d.%m.%Y').date().isoformat()
        m['owner'] = (m.get('owner') or '').strip(); m['portfolio_type'] = (m.get('portfolio_type') or '').strip() or ('dip' if P['kind'] == 'DIP' else 'regular')
        label = m['owner'] or 'own'
        tag = f"{label} / {P['kind']}"
        if len(P['ov']) != len(P['blocks']): checks.append((f'{tag}: overview rows ({len(P["ov"])}) = portfolio blocks ({len(P["blocks"])})', False))
        for b, o in zip(P['blocks'], P['ov']):
            czk_sum = sum(r['czk'] for r in b['rows']) + sum(c['czk'] for c in b['cash'])
            t = P['tx'][b['title']]
            checks.append((f"{tag} / {b['title']}: positions+cash {czk_sum:,.2f} = block total {b['total']:,.2f} = overview end {o['end']:,.2f}", abs(czk_sum - b['total']) < 0.05 and abs(b['total'] - o['end']) < 0.005))
            for r in b['rows']:
                # statement prices are rounded to 2 dp and values to 2 dp -> tolerance: 1 % on qty*price, rounding of value on value*fx
                ok = abs(r['qty'] * r['price'] - r['val']) <= 0.01 * r['val'] + 0.01 and abs(r['val'] * r['fx'] - r['czk']) <= 0.005 * r['fx'] + 0.02
                if not ok: checks.append((f"{tag} / {b['title']} / {r['sym']}: qty*price~value and value*fx=CZK", False))
            acct = f"{label} · {b['title']} · ...{o['vs'][-4:]}"
            note_base = f"{(m.get('holder_note') or '').strip()}{'; ' if (m.get('holder_note') or '').strip() else ''}Portu robo portfolio; statement {P['period'][0]}-{P['period'][1]}; ISIN not on statement; cost basis not on statement (only month flows)"
            for r in b['rows']:
                rows.append(dict(platform='portu', account=acct, portfolio_type=m['portfolio_type'], asset_class='etf', instrument_id=r['sym'], symbol=r['sym'].split()[0], name=NAMES.get(r['sym'], ''),
                    status='held', native_ccy=r['ccy'], units_net=f"{r['qty']:.4f}", report_ccy='CZK', value=f"{r['czk']:.2f}", price=f"{r['price']:.2f}", price_ccy=r['ccy'], valuation_date=asof,
                    confidence='high', notes=note_base + ('' if r['sym'] in NAMES else '; NAME MISSING'), owner=m['owner']))
            for c in b['cash']:
                rows.append(dict(platform='portu', account=acct, portfolio_type=m['portfolio_type'], asset_class='cash', instrument_id=c['ccy'], symbol=c['ccy'], name=f"Cash {c['ccy']} in portfolio",
                    status='held', native_ccy=c['ccy'], units_net=f"{c['amt']:.2f}", report_ccy='CZK', value=f"{c['czk']:.2f}", valuation_date=asof, confidence='high', notes=note_base, owner=m['owner']))
            sect.append((label, P['kind'], b['title'], o, b['total'], t, P['fee_gross'][b['title']], P['fee_disc'][b['title']], len(b['rows'])))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'portu.positions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    own = {}
    for x in sect:
        own[x[0]] = own.get(x[0], 0) + x[4]
    dates = sorted({r['valuation_date'] for r in rows if r.get('valuation_date')})
    vd = dates[-1] if dates else ''
    md = [f"---\nplatform: portu\nsource_type: Portu monthly statements ({len(M)} files)\nvaluation_date: {vd}\ngenerated: {dt.date.today().isoformat()}\nreport_ccy: CZK\npositions_csv: portu.positions.csv\n---\n",
          f"# Portu index\n\nTotals at {vd} (CZK, incl. cash):\n\n| Owner | Total CZK |\n|---|---:|\n"]
    for k, v in own.items():
        md.append(f"| {k} | {v:,.2f} |\n")
    md.append(f"| **All Portu** | **{sum(own.values()):,.2f}** |\n\n## Portfolios\n| Owner | Type | Portfolio | Start of month | End of month | Month return | Deposits | Trades (buy/sell) | Fee net (gross, discount) | Positions |\n|---|---|---|---:|---:|---:|---:|---|---|---:|\n")
    for o_, k, t, o, tot, tx, fg, fd, n in sect:
        md.append(f"| {o_} | {'dip' if k == 'DIP' else 'regular'} | {t} | {o['start']:,.2f} | {tot:,.2f} | {o['yld']:.2f} % | {tx['deposits']:,.2f} | {tx['trades']} ({tx['buys']}/{tx['sells']}) | {tx['fees']:,.2f} ({fg:,.2f}, {fd:,.2f}) | {n} |\n")
    md.append("\n## Reconciliation\n" + (''.join(f"- {'OK' if ok else 'MISMATCH'}: {n}\n" for n, ok in checks) or '- (no checks failed)\n'))
    md.append("""
## Caveats
- Monthly statement: units and values only. No ISINs, no cost basis, no dividends (the ETFs are accumulating). Cost needs the deposit history from the Portu app or other statements.
- Instrument id = Bloomberg-style ticker + exchange (GY = Xetra, LN = London); the same ETFs recur across portfolios, so aggregate by symbol across accounts.
- Prices are month-end closes with the statement's FX; they are not refreshed. A name is filled from a built-in lookup of the ETFs Portu uses; `NAME MISSING` in notes means add the ISIN with `scripts/instruments_add.py`.
- Platform background (public reviews, may change): robo-advisor that builds portfolios of broad UCITS ETFs per risk profile and rebalances automatically; fee is a monthly % of assets with discounts; a DIP wrapper is available with its own tax rules.
- Rebuild: `python3 -I parsers/portu_index.py <manifest.csv> --out data/index`
""")
    open(os.path.join(out, 'portu.index.md'), 'w', encoding='utf-8').write(''.join(md))
    for n, ok in checks:
        print('OK ' if ok else 'MISMATCH', n)
    print(f'OK portu: {len(rows)} rows')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('manifest'); ap.add_argument('--out', default='data/index')
    a = ap.parse_args(); main(a.manifest, a.out)

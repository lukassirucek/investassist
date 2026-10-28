#!/usr/bin/env python3
"""Revolut "Consolidated statement" (xlsx, Investment Services Summaries) -> data/index/revolut.positions.csv + revolut.index.md

Usage: python3 -I parsers/revolut_index.py <statement.xlsx> [--out data/index] [--report-ccy GBP] [--portfolio-type regular]
         [--screens app_screenshots.csv --screens-date YYYY-MM-DD [--app-total N]] [--aliases aliases.json] [--source-url URL]
Needs: pip install openpyxl.  Contract of the output: docs/index-spec.md.

The statement holds every trade since opening: units bought/sold, amounts invested, realised P&L, dividends, crypto buys and staking. It has NO market values
for stocks. Market value, price and cash come from an optional transcription of the app's list screens (`--screens`, columns:
symbol,name,units_shown,price,price_ccy,value_<ccy>,return_pct,screenshot,asset_class  with asset_class stock|etf|crypto|cash and a row `CASH_<ccy>`,
value column named value_gbp / value_eur / value_usd per the report currency). App list screens truncate units to 2 decimals: they are only cross-checked.
Without screens, `value` stays blank for stocks (never estimated); crypto values come from the statement's end-of-year holding table.

--aliases JSON for corporate actions the statement cannot show (all keys optional):
  {"isin_alias":   {"<ISIN seen in sold/dividend rows>": ["<ISIN of the position>", <units multiplier or null>]},
   "screen_alias": {"<app symbol>": "<ISIN>"},                 # app symbol -> position ISIN when the statement has no purchase
   "split_confirmed": ["CRWD"],                                # symbols whose unit mismatch (integer ratio) you confirmed is a split
   "merge": [{"from_isin": "...", "to_symbol": "CDE", "to_isin": "...", "note": "merger conversion"}],
   "crypto_notes": {"NEAR": "bought for ... in the app"}}
Unexplained differences are never fixed silently; they are listed under "App screenshot cross-check" and in the reconciliation table.
"""
import argparse, csv, datetime as dt, json, math, os, re, sys

try:
    import openpyxl
except ImportError:
    sys.exit('openpyxl is required: pip install openpyxl')

COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']
SYM = {'£': 'GBP', '$': 'USD', '€': 'EUR'}


def fix(s):
    if not isinstance(s, str):
        return s
    s = re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), s)
    try:
        s = s.encode('latin-1').decode('utf-8')      # statement text has mojibake (Â£, â€™)
    except Exception:
        pass
    return s.replace('&amp;', '&')


def money(v):
    """-> (value float|None, ccy|None)"""
    if v is None:
        return None, None
    if isinstance(v, (int, float)):
        return float(v), None
    s = fix(v).strip()
    ccy = next((SYM[c] for c in SYM if c in s), None)
    num = re.sub(r'[^0-9.]', '', s)
    if not num:
        return None, ccy
    x = float(num)
    return (-x if '-' in s else x), ccy


def d(v):
    return v.date() if isinstance(v, dt.datetime) else v


def apply_screens(rows, scr_path, scr_date, app_total, rc, A, checks):
    scr = {}
    for r in csv.DictReader(open(scr_path, encoding='utf-8-sig')):
        scr[r['symbol']] = r                     # later screenshots override earlier duplicates
    valcol = next((c for c in next(iter(scr.values())) if c.startswith('value_')), None)
    by_isin = {r['instrument_id']: r for r in rows if r['asset_class'] in ('stock', 'etf')}
    by_sym = {r['symbol']: r for r in rows if r['asset_class'] in ('stock', 'etf') and r['symbol']}
    by_crypto = {r['symbol']: r for r in rows if r['asset_class'] == 'crypto'}
    sa = A.get('screen_alias', {})
    seen, mism, used = set(), [], 0.0
    for sym, a in scr.items():
        if a['asset_class'] == 'cash':
            continue
        row = by_crypto.get(sym) if a['asset_class'] == 'crypto' else (by_isin.get(sa[sym]) if sym in sa else by_sym.get(sym))
        if row is None:
            mism.append(f'{sym}: in app, not in index'); continue
        seen.add(id(row))
        shown, val = float(a['units_shown']), float(a[valcol])
        row['value'] = f'{val:.2f}'; row['price'] = a['price']; row['price_ccy'] = a['price_ccy']; row['valuation_date'] = scr_date
        if a['asset_class'] in ('stock', 'etf'):
            used += val
            if row['units_net']:
                if abs(math.floor(float(row['units_net']) * 100 + 1e-9) / 100 - shown) > 1e-9:
                    ratio = shown / float(row['units_net'])
                    if ratio >= 1.9 and abs(ratio - round(ratio)) / round(ratio) < 0.01:
                        ok = sym in A.get('split_confirmed', [])
                        mism.append(f"{sym}: statement units {row['units_net']} x{round(ratio)} = app {shown} - looks like a {round(ratio)}:1 split after purchase" + ('' if ok else ' (NOT confirmed: app units used, please confirm)'))
                        row['notes'] += f" | {round(ratio)}:1 split suspected (statement units pre-split); units from app (2dp)" + ('; confirmed by owner' if ok else '')
                        row['units_net'] = f'{shown:.2f}'; row['confidence'] = 'medium'
                    else:
                        mism.append(f"{sym}: units statement {row['units_net']} vs app {shown} - UNEXPLAINED, check")
            else:
                row['units_net'] = f'{shown:.2f}'; row['confidence'] = 'medium'; row['status'] = 'held'
                row['notes'] = row['notes'].replace('dividends received but no purchase in statement - units unknown, verify in app.', 'no purchase in statement (corporate action).') + ' | units from app screenshot (2dp, truncated)'
        else:
            row['notes'] = (row['notes'] + ' | ' if row['notes'] else '') + f'app {scr_date}: units {shown}' + (f" | {A['crypto_notes'][sym]}" if sym in A.get('crypto_notes', {}) else '')
    for m in A.get('merge', []):                 # e.g. a merger: the old line is converted, cost carries over to the new one
        old, new = by_isin.get(m['from_isin']), by_isin.get(m['to_isin'])
        if old and new and m['to_symbol'] in scr:
            ratio = float(scr[m['to_symbol']]['units_shown']) / float(old['units_net'] or 1)
            old['status'] = 'converted'; old['units_net'] = '0.00000000'
            old['notes'] = f"converted into {m['to_symbol']} - app shows {scr[m['to_symbol']]['units_shown']} for {old['units_bought']} (ratio {ratio:.4f}); {m.get('note', '')}"
            new['cost'], new['fees'] = old['cost'], old['fees']
            new['first_buy'], new['last_buy'] = old['first_buy'], old['last_buy']
            new['notes'] += f" | cost carried over from {old['symbol'] or old['instrument_id']} ({m.get('note', '')})"
    for r in rows:
        if r['asset_class'] in ('stock', 'etf') and r['status'] in ('held', 'held_unverified') and id(r) not in seen:
            mism.append(f"{r['symbol'] or r['name']}: held per statement, not in app")
    cash_key = next((k for k in scr if k.startswith('CASH_')), None)
    cash = float(scr[cash_key][valcol]) if cash_key else None
    if cash is not None:
        ccy = cash_key.split('_', 1)[1]
        rows.append(dict(platform='revolut', account=rows[0]['account'] if rows else 'brokerage', portfolio_type=rows[0]['portfolio_type'] if rows else '', asset_class='cash', instrument_id=ccy,
                         symbol=ccy, name='Cash balance', status='held', native_ccy=ccy, units_net=f'{cash:.2f}', report_ccy=rc, value=f'{cash:.2f}', valuation_date=scr_date,
                         confidence='high', notes='from app screenshot'))
    if app_total is not None:
        tot = used + (cash or 0)
        checks.append((f'stocks value (app screens) + cash vs app total {app_total:,.2f}', round(tot, 2), app_total, 'OK' if abs(tot - app_total) <= 5 else 'MISMATCH'))
    return dict(mismatches=mism, stock_value=used, cash=cash)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('statement'); ap.add_argument('--out', default='data/index'); ap.add_argument('--report-ccy', default=None)
    ap.add_argument('--portfolio-type', default='regular'); ap.add_argument('--source-url', default='')
    ap.add_argument('--screens'); ap.add_argument('--screens-date', default=dt.date.today().isoformat()); ap.add_argument('--app-total', type=float)
    ap.add_argument('--aliases'); ap.add_argument('--owner', default='')
    a = ap.parse_args()
    A = json.load(open(a.aliases, encoding='utf-8')) if a.aliases else {}
    ALIAS = {k: tuple(v) for k, v in A.get('isin_alias', {}).items()}
    path, out = a.statement, a.out

    ws = openpyxl.load_workbook(path, data_only=True).active
    rows = [(i, [fix(c) for c in r if c is not None]) for i, r in enumerate(ws.iter_rows(values_only=True), 1)]

    def find(txt, start=0):
        try:
            return next(i for i, r in rows if i > start and r and isinstance(r[0], str) and r[0].startswith(txt))
        except StopIteration:
            sys.exit(f'Not a Revolut consolidated statement: section "{txt}" not found.')
    r_div, r_sold, r_oth, r_cry = (find('Transaction statement (only dividend'), find('Units which have been sold'),
                                   find('Other brokerage account transactions'), find('Crypto Transaction Statements'))
    r_eoy = find('End of Year holding statement')
    acct = next(r for i, r in rows if r and r[0] == 'Account Number')[1]
    acct_mask = '…' + str(int(float(acct)))[-4:]
    period = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})', os.path.basename(path))
    rc = (a.report_ccy or next((money(c)[1] for i, r in rows[:25] for c in r if isinstance(c, str) and money(c)[1]), None) or 'GBP').upper()
    summ = {}
    labels = ('Dividends', 'Tax withheld on dividend', 'Net dividend income', 'Gross proceeds', 'Cost basis', 'Fees and other charges', 'Net PnL')
    for i, r in rows[:20]:
        for k in range(0, len(r) - 1, 2):
            if r[k] in labels:
                summ[r[k]] = money(r[k + 1])[0]
    pos = {}

    def P(isin):
        return pos.setdefault(isin, dict(isin=isin, symbol='', name='', country='', native_ccy='', units_bought=0.0, units_sold=0.0, n_buys=0, first_buy='', last_buy='', cost=0.0, fees=0.0,
                                         proceeds=0.0, realized=0.0, div_gross=0.0, div_tax=0.0, div_net=0.0, n_div=0, last_div='', notes=[]))
    for i, r in rows:                                                  # buys
        if r_oth < i < r_cry and len(r) in (10, 15) and isinstance(r[0], dt.datetime):
            date, sym, isin, qty, country = d(r[0]), r[1], r[2], float(r[3]), r[4]
            if len(r) == 15:
                gross_n, gross_g, fee_g = r[5], money(r[6])[0], money(r[12])[0]
                ccy = money(gross_n)[1] or 'USD'                       # numeric-only native amounts are assumed USD
            else:
                gross_g, fee_g, ccy = money(r[5])[0], money(r[8])[0], rc
            p = P(isin); p.update(symbol=sym, country=country)
            p['native_ccy'] = p['native_ccy'] or ccy
            p['units_bought'] += qty; p['n_buys'] += 1; p['cost'] += gross_g; p['fees'] += fee_g
            ds = date.isoformat(); p['first_buy'] = min(p['first_buy'] or ds, ds); p['last_buy'] = max(p['last_buy'], ds)
    sold_tot = dict(proceeds=0.0, cost=0.0, pnl=0.0)
    for i, r in rows:                                                  # sold lots
        if r_sold < i < r_oth and len(r) >= 17 and isinstance(r[0], dt.datetime):
            isin_s, units = r[3], float(r[6])
            proceeds, cost, pnl = money(r[13])[0], abs(money(r[14])[0]), money(r[16])[0]
            sold_tot['proceeds'] += proceeds; sold_tot['cost'] += cost; sold_tot['pnl'] += pnl
            tgt, mult = ALIAS.get(isin_s, (isin_s, 1.0))
            p = P(tgt); p['units_sold'] += units * (mult or 1.0); p['proceeds'] += proceeds; p['realized'] += pnl
            if isin_s != tgt:
                p['notes'].append(f'sold under alias {isin_s} (corporate action)')
            if not p['name']:
                p['name'] = re.sub(r'\s+\S+$', '', r[2])
    div_tot = dict(gross=0.0, tax=0.0, net=0.0)
    for i, r in rows:                                                  # dividends
        if r_div < i < r_sold and len(r) == 14 and isinstance(r[0], dt.datetime):
            isin = r[2]; tgt, _ = ALIAS.get(isin, (isin, 1)); p = P(tgt)
            nm = r[1].replace(' dividend', '')
            if isin != tgt:
                p['notes'].append(f'dividends received on alias ISIN {isin} ({nm})')
            p['name'] = p['name'] or nm; p['country'] = p['country'] or r[3]
            g, t, n = money(r[5])[0], money(r[7])[0], money(r[13])[0]
            p['div_gross'] += g; p['div_tax'] += t; p['div_net'] += n; p['n_div'] += 1
            p['last_div'] = max(p['last_div'], d(r[0]).isoformat())
            div_tot['gross'] += g; div_tot['tax'] += t; div_tot['net'] += n
    for p in pos.values():                                             # status
        net = p['units_bought'] - p['units_sold']
        net = 0.0 if abs(net) < 1e-6 else net
        p['units_net'] = round(net, 8) if p['units_bought'] else None
        if p['units_bought'] == 0 and p['units_sold'] > 0:
            p['status'] = 'sold_out'; p['units_net'] = 0.0; p['notes'].append('received via corporate action (no purchase), then sold')
        elif p['units_bought'] == 0:
            p['status'] = 'held_unverified'; p['notes'].append('dividends received but no purchase in statement - units unknown, verify in app.')
        elif net < 1e-6:
            p['status'] = 'sold_out'
        else:
            p['status'] = 'held'
    crypto, eoy_val = {}, {}                                           # crypto
    for i, r in rows:
        if r_eoy < i < r_eoy + 10 and len(r) == 4 and r[0] != 'Description & symbol' and isinstance(r[1], (int, float)):
            eoy_val[r[0]] = dict(units=float(r[1]), price=money(r[2])[0], value=money(r[3])[0])
    cbuy_tot, stake_tot, sec = [0.0, 0.0], 0.0, None
    for i, r in rows:
        if i <= r_cry:
            continue
        if r and isinstance(r[0], str) and r[0].startswith('Transaction statement (only acquisitions via'):
            sec = 'stake'; continue
        if r and isinstance(r[0], str) and r[0].startswith('Transaction statement (only acquisitions)'):
            sec = 'buy'; continue
        if sec and len(r) == 6 and re.match(r'\d\d\.\d\d\.\d\d$', str(r[0])):
            dd = dt.datetime.strptime(r[0], '%d.%m.%y').date().isoformat()
            c = crypto.setdefault(r[1], dict(units_buy=0.0, units_stake=0.0, cost=0.0, fees=0.0, stake_value=0.0, first=dd, last=dd, n=0))
            u, val, fee = float(r[2]), money(r[4])[0], money(r[5])[0]
            if sec == 'buy':
                c['units_buy'] += u; c['cost'] += val; c['fees'] += fee; cbuy_tot[0] += val; cbuy_tot[1] += fee
            else:
                c['units_stake'] += u; c['stake_value'] += val; stake_tot += val
            c['first'] = min(c['first'], dd); c['last'] = max(c['last'], dd); c['n'] += 1
    checks = []

    def chk(name, got, exp, tol=0.05):
        checks.append((name, round(got, 2), exp, 'OK' if exp is not None and abs(got - exp) <= tol else 'MISMATCH'))
    chk(f'dividends gross {rc}', div_tot['gross'], summ.get('Dividends'), 0.15)
    chk(f'dividends tax {rc}', div_tot['tax'], summ.get('Tax withheld on dividend'), 0.15)
    chk(f'dividends net {rc}', div_tot['net'], summ.get('Net dividend income'), 0.15)
    chk(f'sold proceeds {rc}', sold_tot['proceeds'], summ.get('Gross proceeds'))
    chk(f'sold cost basis {rc}', sold_tot['cost'], summ.get('Cost basis'))
    chk(f'realized P&L after fees {rc}', sold_tot['pnl'] - (summ.get('Fees and other charges') or 0), summ.get('Net PnL'))
    ctot = [r for i, r in rows if i > r_cry and r and r[0] == 'Total']
    chk(f'crypto purchases {rc}', cbuy_tot[0], money(ctot[0][1])[0] if ctot else None, 0.1)
    chk(f'crypto staking {rc}', stake_tot, money(ctot[1][1])[0] if len(ctot) > 1 else None, 0.05)
    for sym, c in crypto.items():
        if sym in eoy_val:
            chk(f'crypto units {sym}', c['units_buy'] + c['units_stake'], eoy_val[sym]['units'], 1e-6)

    own = a.owner
    out_rows = []
    for p in sorted(pos.values(), key=lambda p: -p['cost']):
        out_rows.append(dict(platform='revolut', account=acct_mask + ' (brokerage)', portfolio_type=a.portfolio_type, asset_class='etf' if re.search(r'\bETF|UCITS|\bETC\b', p['name'], re.I) else 'stock',
                             instrument_id=p['isin'], symbol=p['symbol'], name=p['name'], country=p['country'], status=p['status'], native_ccy=p['native_ccy'],
                             units_net='' if p['units_net'] is None else f"{p['units_net']:.8f}", units_bought=f"{p['units_bought']:.8f}", units_sold=f"{p['units_sold']:.8f}", n_buys=p['n_buys'],
                             first_buy=p['first_buy'], last_buy=p['last_buy'], report_ccy=rc, cost=f"{p['cost']:.2f}", fees=f"{p['fees']:.2f}", realized_pnl=f"{p['realized']:.2f}",
                             dividends_gross=f"{p['div_gross']:.2f}", dividends_tax=f"{p['div_tax']:.2f}", dividends_net=f"{p['div_net']:.2f}", n_dividends=p['n_div'], last_dividend=p['last_div'],
                             confidence='medium' if p['status'] != 'held_unverified' else 'low', notes='; '.join(p['notes']), owner=own))
    val_date = period.group(2) if period else ''
    for sym, c in crypto.items():
        e = eoy_val.get(sym, {})
        out_rows.append(dict(platform='revolut', account='crypto (Revolut Ltd)', portfolio_type='', asset_class='crypto', instrument_id=sym, symbol=sym, status='held', native_ccy=rc,
                             units_net=f"{c['units_buy'] + c['units_stake']:.8f}", units_bought=f"{c['units_buy']:.8f}", units_sold='0.00000000', n_buys=c['n'], first_buy=c['first'], last_buy=c['last'],
                             report_ccy=rc, cost=f"{c['cost']:.2f}", fees=f"{c['fees']:.2f}", realized_pnl='0.00', dividends_net=f"{c['stake_value']:.2f}",
                             value=f"{e.get('value', 0):.2f}" if e else '', price=f"{e.get('price', 0):.2f}" if e else '', price_ccy=rc if e else '', valuation_date=val_date, confidence='high',
                             notes='dividends_net column = staking income at receipt' if c['units_stake'] else '', owner=own))
    scr_info = apply_screens(out_rows, a.screens, a.screens_date, a.app_total, rc, A, checks) if a.screens else None
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'revolut.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore'); w.writeheader(); w.writerows(out_rows)

    stocks = [r for r in out_rows if r['asset_class'] in ('stock', 'etf')]
    held = sorted([r for r in stocks if r['status'] in ('held', 'held_unverified')], key=lambda r: -(float(r['value']) if r.get('value') else 0))
    gone = [r for r in stocks if r['status'] in ('sold_out', 'converted')]
    cash_val = sum(float(r['value']) for r in out_rows if r['asset_class'] == 'cash')
    stock_val = sum(float(r['value']) for r in held if r.get('value'))
    crypto_rows = [r for r in out_rows if r['asset_class'] == 'crypto']
    crypto_val = sum(float(r['value'] or 0) for r in crypto_rows)
    md = [f"""---
platform: revolut
source_type: Revolut consolidated statement (xlsx)
source_file: {os.path.basename(path)}
source_url: {a.source_url}
statement_period: {period.group(1) + ' to ' + period.group(2) if period else ''}
valuation_date: {a.screens_date if a.screens else val_date}
generated: {dt.date.today().isoformat()}
report_ccy: {rc}
positions_csv: revolut.positions.csv
---
# Revolut index

Every instrument traded on Revolut (stocks/ETFs + crypto) since account opening: units, amount invested, realised P&L, dividend income. Amounts in **{rc}** (statement currency).

## Totals ({rc})
| | |
|---|---|
| Stock/ETF positions held | {len(held)} (+{len(gone)} sold out/converted) |
| Stocks/ETFs market value (app screens{', ' + a.screens_date if a.screens else ': none given, values blank'}) | {stock_val:,.2f} |
| Cash balance | {cash_val:,.2f} |
| Stocks cost of held positions | {sum(float(r['cost']) for r in held):,.2f} |
| Realised P&L (sold lots, before {summ.get('Fees and other charges', 0) or 0:.2f} fees) | {sold_tot['pnl']:+,.2f} |
| Dividends gross / tax / net | {div_tot['gross']:,.2f} / {div_tot['tax']:,.2f} / {div_tot['net']:,.2f} |
| Crypto cost / value | {sum(float(r['cost']) for r in crypto_rows):,.2f} / {crypto_val:,.2f} |
| **Total (stocks + cash + crypto)** | **{stock_val + cash_val + crypto_val:,.2f}** |

## Held stocks/ETFs (by market value)
| Symbol | Name | ISIN | Units | Price | Value | Cost | Div net | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
"""]
    for r in held:
        md.append(f"| {r['symbol'] or '-'} | {r['name'] or '-'} | {r['instrument_id']} | {r['units_net'] or '?'} | {(r['price'] + ' ' + r['price_ccy']) if r.get('price') else '-'} | {r.get('value') or '-'} | {r['cost']} | {r['dividends_net']} | {r['status']} |\n")
    md.append("\n## Crypto\n| Symbol | Units | Cost | Value |\n|---|---:|---:|---:|\n" + ''.join(f"| {r['symbol']} | {r['units_net']} | {r['cost']} | {r['value'] or '-'} |\n" for r in crypto_rows))
    md.append("\n## Sold out / converted\n" + (', '.join(f"{r['symbol'] or r['name']} ({r['status']}, P&L {r['realized_pnl']})" for r in gone) or 'none') + "\n")
    if scr_info:
        md.append("\n## App screenshot cross-check\n" + (''.join(f"- {m}\n" for m in scr_info['mismatches']) or "- all held positions match (units equal to statement, truncated to 2dp)\n"))
    md.append("\n## Reconciliation vs statement summary\n| Check | Computed | Statement | Result |\n|---|---:|---:|---|\n" + ''.join(f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} |\n" for c in checks))
    md.append(f"""
## Caveats
- `cost` = gross amount paid at purchase in {rc} (fees separate). `value` / `price` exist only when app screens were provided: a snapshot, not a feed.
- Units are as of transaction date. Splits, mergers and spin-offs after purchase are not in the statement; unexplained unit differences are listed above. Use `--aliases` for confirmed corporate actions.
- Names appear in the statement only for sold and dividend rows; enrichment (sector, region) is done by `build-exposure-map` via ISIN.
- Native currency of numeric-only amounts is assumed USD.
- Rebuild: `python3 -I parsers/revolut_index.py <statement.xlsx> --out data/index [--screens ... --screens-date ...]`
""")
    open(os.path.join(out, 'revolut.index.md'), 'w', encoding='utf-8').write(''.join(md))
    for c in checks:
        print(c)
    if scr_info:
        print('screens:', scr_info['mismatches'])
    print(f'OK revolut: {len(stocks)} stock rows; {len(held)} held; {len(crypto_rows)} crypto')


if __name__ == '__main__':
    main()

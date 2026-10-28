#!/usr/bin/env python3
"""Indigo (Patria Finance, Czech ETF robo-advisor) quarterly statement e-mail saved as HTML ("Pravidelný výpis z účtu")
-> data/index/indigo.positions.csv + indigo.index.md

Usage: python3 -I parsers/indigo_index.py <mail.html> [--out data/index] [--source-url URL] [--owner NAME]
Save the statement mail as .html (Gmail: "Show original" / download message, or export from your mail client). No other dependency.
Statement is QUARTERLY: holdings are as of period end, transactions only cover the quarter => cost basis unknown
(cost left blank; the quarter's flows go to units_bought/units_sold/n_buys). Report currency = CZK (the statement's currency).
Reconciles positions, cash, deposits and fees against the statement header.
"""
import csv, datetime as dt, html, os, re, sys
from collections import OrderedDict

def to_text(raw):
    t = raw.decode('utf-8', errors='replace')
    t = re.sub(r'(?is)<(script|style|head).*?</\1>', '', t)
    t = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', t)
    t = re.sub(r'(?i)</t[dh]>', ' | ', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    t = re.sub(r'[ \t\xa0 ​]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t)

def num(s):
    s = re.sub(r'[^0-9,.\-]', '', s.replace('\xa0', '').replace(' ', ''))
    if s in ('', '-'):
        return None
    return float(s.replace(',', '.'))

def cz_date(s):
    return dt.datetime.strptime(s[:10], '%d.%m.%Y').date().isoformat()

def main(path, out='data/index', src_url='', owner=''):
    text = to_text(open(path, 'rb').read())
    lines = [l.strip() for l in text.split('\n')]
    # --- header
    def kv(label):
        for l in lines:
            if l.startswith(label):
                return l.split(':', 1)[1].strip()
        return None
    per = re.search(r'za období (\d\d\.\d\d\.\d{4}) - (\d\d\.\d\d\.\d{4})', text)
    p_from, p_to = cz_date(per.group(1)), cz_date(per.group(2))
    H = dict(goal=kv('Investiční cíl'), profile=kv('Portfolio:'), start=num(kv('Počáteční hodnota investic')), end=num(kv('Konečná hodnota investic')),
             perf=num(kv('Výkonnost investic za období')), cash0=num(kv('Počáteční hotovostní zůstatek')), cash1=num(kv('Konečný hotovostní zůstatek')),
             deposits=num(kv('Vklady')), withdrawals=num(kv('Výběry')), dividends=num(kv('Dividendy a připsané úroky')), fee=num(kv('Poplatek')),
             check=kv('Vyhodnocení'))
    # --- holdings
    i0 = next(i for i, l in enumerate(lines) if l.startswith('Stav investovaného majetku'))
    i1 = next(i for i, l in enumerate(lines) if i > i0 and l.startswith('Provedené transakce'))
    hold, cash = OrderedDict(), []
    for l in lines[i0:i1]:
        c = [x.strip() for x in l.split('|')]
        if len(c) >= 7 and re.match(r'^[A-Z]{2}[A-Z0-9]{9}\d$', c[0]):
            hold[c[0]] = dict(name=c[1], ccy=c[2], units=num(c[3]), price=num(c[4]), value_native=num(c[5]), value_czk=num(c[6]))
        elif len(c) >= 7 and c[0] in ('CZK', 'USD', 'EUR'):
            cash.append(dict(ccy=c[0], name=c[1], value_czk=num(c[6])))
    # --- transactions
    tx = []
    for l in lines[i1:]:
        c = [x.strip() for x in l.split('|')]
        if len(c) >= 9 and re.match(r'^\d\d\.\d\d\.\d{4}', c[0]):
            tx.append(dict(date=cz_date(c[0]), kind=c[1], instr=c[2], isin=c[3], ccy=c[4], units=num(c[6]), price=num(c[7]), amount=num(c[8])))
    inst = OrderedDict()
    for t in tx:
        if t['kind'] in ('Nákup', 'Prodej'):
            d = inst.setdefault(t['isin'], dict(name=t['instr'], ccy=t['ccy'], buy_u=0.0, sell_u=0.0, n_buy=0, first='', last='', last_kind='', buy_amt=0.0, sell_amt=0.0))
            if t['kind'] == 'Nákup':
                d['buy_u'] += t['units']; d['n_buy'] += 1; d['buy_amt'] += -t['amount']
            else:
                d['sell_u'] += t['units']; d['sell_amt'] += t['amount']
            d['first'] = min(d['first'] or t['date'], t['date']); d['last'] = max(d['last'], t['date']); d['last_kind'] = t['kind']
    cz = lambda k: [t for t in tx if t['kind'].startswith(k) and t['ccy'] == 'CZK']
    sums = dict(deposits=sum(t['amount'] for t in cz('Vklad')), fees=-sum(t['amount'] for t in cz('Poplatek')), interest=sum(t['amount'] for t in cz('Kreditní úrok')),
                div_usd=sum(t['amount'] for t in tx if t['kind'] == 'Výplata dividendy'))
    pos_sum = sum(h['value_czk'] for h in hold.values()); cash_sum = sum(c['value_czk'] for c in cash)
    checks = []
    def chk(n, got, exp, tol=0.05):
        checks.append((n, round(got, 2), exp, 'OK' if exp is not None and abs(got - exp) <= tol else 'MISMATCH'))
    chk('sum positions CZK = closing investments value', pos_sum, H['end'])
    chk('sum cash CZK = closing cash balance', cash_sum, H['cash1'], 0.01)
    chk('sum "Vklad penez" CZK = deposits', sums['deposits'], H['deposits'], 0.01)
    chk('sum management fees CZK = fee', sums['fees'], H['fee'], 0.01)
    # --- csv
    cols = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
            'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends',
            'last_dividend', 'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner']
    rows = []
    for isin, h in hold.items():
        f = inst.get(isin, {})
        rows.append(dict(platform='indigo', account='Indigo (Patria Finance a.s.)', asset_class='etf', instrument_id=isin, symbol='', name=h['name'], country='',
            status='held', native_ccy=h['ccy'], units_net=f"{h['units']:.4f}", units_bought=f"{f.get('buy_u', 0):.4f}" if f else '', units_sold=f"{f.get('sell_u', 0):.4f}" if f else '',
            n_buys=f.get('n_buy', '') if f else '', first_buy=f.get('first', ''), last_buy=f.get('last', ''), report_ccy='CZK', cost='', value=f"{h['value_czk']:.2f}",
            price=f"{h['price']}", price_ccy=h['ccy'], valuation_date=p_to, confidence='high',
            notes=f"value_native {h['ccy']} {h['value_native']}; cost basis unknown (quarterly statement); units_bought/sold/n_buys cover {p_from}..{p_to} only"))
    for isin, f in inst.items():
        if isin in hold:
            continue
        gone = f['last_kind'] == 'Prodej'
        rows.append(dict(platform='indigo', account='Indigo (Patria Finance a.s.)', asset_class='etf', instrument_id=isin, symbol='', name=f['name'], country='',
            status='sold_out' if gone else 'held_unverified', native_ccy=f['ccy'], units_net='0.0000' if gone else '', units_bought=f"{f['buy_u']:.4f}", units_sold=f"{f['sell_u']:.4f}",
            n_buys=f['n_buy'], first_buy=f['first'], last_buy=f['last'], report_ccy='CZK', cost='', valuation_date=p_to, confidence='medium',
            notes=('fully sold within quarter' if gone else f"bought on {f['last']} ({f['ccy']} {f['buy_amt']:.2f}) but absent from period-end holdings - likely unsettled; check next statement")))
    for c in cash:
        rows.append(dict(platform='indigo', account='Indigo (Patria Finance a.s.)', asset_class='cash', instrument_id=c['ccy'], symbol=c['ccy'], name=c['name'], status='held',
            native_ccy=c['ccy'], report_ccy='CZK', value=f"{c['value_czk']:.2f}", valuation_date=p_to, confidence='high',
            notes='statement shows the CZK value only' if c['ccy'] != 'CZK' else ''))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'indigo.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        [r.update(owner=owner) for r in rows]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    # --- md
    total = pos_sum + cash_sum
    md = [f"""---
platform: indigo
provider: Patria Finance a.s. (Indigo robo-advisor, ČSOB group)
source_file: {os.path.basename(path)}
source_url: {src_url}
statement_period: {p_from} to {p_to}
statement_type: quarterly e-mail statement (Pravidelný výpis z účtu)
generated: {dt.date.today().isoformat()}
report_ccy: CZK
positions_csv: indigo.positions.csv
portfolio_profile: {H['profile']} (goal: {H['goal']}); suitability check: {H['check']}
---
# Indigo index

**What it is:** Indigo (Patria Finance) ETF robo-portfolio, positions and cash as of **{p_to}**. Amounts in **CZK** (value in native currency in `notes`). Query `indigo.positions.csv`.

## Totals (CZK)
| | |
|---|---:|
| Investments ({len(hold)} ETFs) at {p_to} | {pos_sum:,.2f} |
| Cash (CZK + USD balance) | {cash_sum:,.2f} |
| **Total** | **{total:,.2f}** |
| Cash share of total | {cash_sum / total * 100:.1f} % |
| Deposits / withdrawals in the quarter | {H['deposits']:,.2f} / {H['withdrawals']:,.2f} |
| Performance in the quarter (statement) | {H['perf']} % |
| Management fees in the quarter | {H['fee']:,.2f} |
| Start value (investments) | {H['start']:,.2f} |

## Positions (by value)
| ISIN | Instrument | Ccy | Units | Price | Value CZK | Share of investments |
|---|---|---|---:|---:|---:|---:|
"""]
    for isin, h in sorted(hold.items(), key=lambda kv: -kv[1]['value_czk']):
        md.append(f"| {isin} | {h['name']} | {h['ccy']} | {h['units']:.4f} | {h['price']} | {h['value_czk']:,.2f} | {h['value_czk'] / pos_sum * 100:.1f} % |\n")
    other = [r for r in rows if r['asset_class'] == 'etf' and r['status'] != 'held']
    if other:
        md.append("\n## Traded in the quarter, not in period-end holdings\n" + ''.join(f"- {r['name']} ({r['instrument_id']}): {r['status']} - {r['notes']}\n" for r in other))
    md.append("\n## Reconciliation vs statement header\n| Check | Computed | Statement | Result |\n|---|---:|---:|---|\n")
    for c in checks:
        md.append(f"| {c[0]} | {c[1]} | {c[2] if c[2] is not None else '-'} | {c[3]} |\n")
    md.append(f"""
## Caveats
- **Quarterly statement:** transactions cover only {p_from}..{p_to}. **Cost basis, P&L since inception and earlier deposits are unknown.** Add earlier statements to extend; the index keeps `cost` blank rather than guess.
- Header "dividends and interest" ({H['dividends']} Kč) matches the USD dividends only (USD {sums['div_usd']:.2f}); CZK credit interest of {sums['interest']:.2f} Kč is listed separately in the transactions.
- Cash is about {cash_sum / total * 100:.0f} % of the account (CZK {cash_sum:,.0f}), uninvested at period end after deposits of {H['deposits']:,.0f}.
- Fund names are as printed by Indigo; no sector/region enrichment yet (`build-exposure-map`).
- Rebuild: `python3 -I parsers/indigo_index.py <mail.html> --out data/index`
""")
    open(os.path.join(out, 'indigo.index.md'), 'w', encoding='utf-8').write(''.join(md))
    for c in checks:
        print(c)
    print(f'OK indigo: {len(hold)} positions; {len(cash)} cash rows; {len(other)} other instruments')

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('mail_html'); ap.add_argument('--out', default='data/index'); ap.add_argument('--source-url', default=''); ap.add_argument('--owner', default='')
    a = ap.parse_args(); main(a.mail_html, a.out, a.source_url, a.owner)

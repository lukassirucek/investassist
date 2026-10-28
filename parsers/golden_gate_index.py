#!/usr/bin/env python3
"""Golden Gate (Czech precious-metals and bitcoin platform) typed figures -> data/index/golden_gate.positions.csv + golden_gate.index.md

Usage: python3 -I parsers/golden_gate_index.py <golden_gate_manual.csv> [--out data/index] [--asof YYYY-MM-DD] [--ccy CZK] [--owner NAME]
SCOPE: only what is held INSIDE the platform: the gold account (regular purchases accumulate towards the next 1 oz brick) and the bitcoin account.
Delivered bricks leave the platform: type them as your own physical holding (examples/typed/physical_gold.example.csv, platform `physical_gold`).
The platform shows only the amount REMAINING to complete the current brick, so accumulated grams are derived: 1 troy oz (31.1034768 g) minus the remaining grams.
Input rows (row_type `state`; columns row_type,account,item,value,unit,note):
  gold_account / remaining_to_complete_brick_g     grams still missing to complete the brick (as shown)
  gold_account / remaining_to_complete_brick_<ccy> price of that remainder at the platform's gold price (e.g. remaining_to_complete_brick_czk)
  gold_account / cash_paid_toward_current_brick_<ccy>   optional: cash paid so far (from payment e-mails) = cost
  btc_account  / units                              BTC shown by the platform
  btc_account  / invested                           total invested in the platform's currency (no market value is shown: leave BTC value blank, the exposure map needs a BTC price)
"""
import argparse, csv, datetime as dt, os, re

OZ = 31.1034768
COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('manual'); ap.add_argument('--out', default='data/index'); ap.add_argument('--asof', default=dt.date.today().isoformat()); ap.add_argument('--ccy', default=None); ap.add_argument('--owner', default='')
    a = ap.parse_args()
    S = {(r['account'], r['item']): float(r['value']) for r in csv.DictReader(open(a.manual, encoding='utf-8-sig')) if r['row_type'] == 'state' and r.get('value') not in (None, '')}
    keys = [k for k in S if k[0] == 'gold_account' and re.fullmatch(r'remaining_to_complete_brick_[a-z]{3}', k[1])]
    ccy = (a.ccy or (keys[0][1][-3:] if keys else 'czk')).upper()
    rem_g, rem_val = S[('gold_account', 'remaining_to_complete_brick_g')], S[('gold_account', f'remaining_to_complete_brick_{ccy.lower()}')]
    price_g = rem_val / rem_g                                   # platform price per gram implied by the remainder
    acc_g = OZ - rem_g
    paid = S.get(('gold_account', f'cash_paid_toward_current_brick_{ccy.lower()}'))
    base = dict(platform='golden_gate', portfolio_type='', country='CZ', status='held', report_ccy=ccy, price_ccy=ccy, valuation_date=a.asof, owner=a.owner)
    rows = [dict(base, account='Golden Gate - gold account (accumulating towards next 1 oz brick)', asset_class='gold', instrument_id='XAU', symbol='XAU', name='Gold (grams, accumulating to 1 oz brick)',
                 native_ccy=ccy, units_net=f'{acc_g:.4f}', value=f'{acc_g * price_g:.2f}', price=f'{price_g:.2f}', cost=(f'{paid:.2f}' if paid else ''), confidence='medium',
                 notes=f'units in GRAMS, derived: 1 oz ({OZ:.4f} g) - remaining {rem_g:g} g; remaining to complete = {rem_val:,.0f} {ccy} at platform price; cost = cash paid toward current brick (payment e-mails); '
                       'delivery to home when completed - then it leaves this platform')]
    has_btc = ('btc_account', 'units') in S
    if has_btc:
        u, inv = S[('btc_account', 'units')], S.get(('btc_account', 'invested'))
        rows.append(dict(base, account='Golden Gate - bitcoin account', asset_class='crypto', instrument_id='BTC', symbol='BTC', name='Bitcoin', native_ccy=ccy, units_net=f'{u:.8f}', units_bought=f'{u:.8f}',
                         cost=f'{inv:.2f}' if inv else '', price=f'{inv / u:.2f}' if inv and u else '', valuation_date='', confidence='medium', value='',
                         notes='cost = total invested as stated (fees unknown); price column = AVERAGE purchase price (derived); the platform shows no market value (needs a BTC price)'))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'golden_gate.positions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    gold_total = acc_g * price_g
    md = f"""---
platform: golden_gate
source_type: typed by owner from the platform
valuation_date: {a.asof}
generated: {dt.date.today().isoformat()}
report_ccy: {ccy} (gold units in grams)
positions_csv: golden_gate.positions.csv
---
# Golden Gate index

Platform holdings only: the **gold account** (regular purchases accumulate towards a 1 oz brick; a completed brick is delivered and leaves the platform) and the **bitcoin account**.
Delivered bricks are your own holding, tracked separately as platform `physical_gold`.

## Gold (inside platform)
| | Grams | Troy oz | Value {ccy} | Cost {ccy} |
|---|---:|---:|---:|---:|
| In account, towards next brick (derived) | {acc_g:.2f} | {acc_g / OZ:.3f} | {gold_total:,.0f} | {paid or 0:,.0f} |
| Remaining to complete brick | {rem_g:g} | {rem_g / OZ:.3f} | {rem_val:,.0f} | |

Platform price implied by the remainder: **{price_g:,.2f} {ccy}/g** ({price_g * OZ:,.0f} {ccy}/oz).
"""
    if has_btc:
        md += f"\n## Bitcoin\n| Units | Invested {ccy} | Avg purchase price | Market value |\n|---:|---:|---:|---|\n| {u:.8f} BTC | {(inv or 0):,.0f} | {(inv / u if inv and u else 0):,.0f} | not provided |\n"
    md += """
## Caveats
- Gold cost = cash paid toward the current brick (from payment e-mails); bonus grams bought with credits carry no cash cost. Accumulated grams are derived, so a small gap to the e-mails is normal.
- Gold value uses the platform price, which likely includes a premium over resale value.
- Bitcoin here is in addition to any BTC on other platforms: aggregate by `instrument_id` = BTC.
- Rebuild: `python3 -I parsers/golden_gate_index.py <golden_gate_manual.csv> --out data/index`
"""
    open(os.path.join(a.out, 'golden_gate.index.md'), 'w', encoding='utf-8').write(md)
    print(f'OK golden_gate: price {price_g:.2f} {ccy}/g; in-account {acc_g:.4f} g = {gold_total:,.0f} {ccy}')


if __name__ == '__main__':
    main()

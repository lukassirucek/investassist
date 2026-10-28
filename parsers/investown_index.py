#!/usr/bin/env python3
"""Investown (Czech real-estate crowdlending) app screenshots, transcribed to two CSVs -> data/index/investown.positions.csv + investown.index.md

Usage: python3 -I parsers/investown_index.py <projects.csv> <summary.csv> [--out data/index] [--asof YYYY-MM-DD] [--ccy CZK] [--owner NAME]
Investown has no export; read the app's overview, portfolio and "my investments" screens (view the images, do not trust OCR) and type them into:
  projects.csv  one row per itemised project: project, max_rate_pct, my_rate_pct, status, next_payout, my_investment, paid_yields, ends_in, screenshot, note
                (`my_investment` / `my_investment_czk` and `paid_yields` / `paid_yields_czk` both accepted; names are truncated in the app: keep them as shown)
  summary.csv   key,value,unit,source with at least: total_value, free_money, portfolio_value, active_investments, repaying_on_time, in_extension, in_recovery
                optional: total_profit, avg_yield_indicative, projects_total, share_repaid_pct, share_repaying_pct, share_extension_pct, share_recovery_pct, share_writtenoff_pct,
                paid_month, planned_month, paid_month_bonuses, tier, tier_bonus_pct, next_tier, next_tier_bonus_pct, to_next_tier
Only some projects are usually itemised (the app scrolls); the rest becomes one remainder row so the total reconciles with the app. Cost = value = amount invested
(assumption: current outstanding principal; accrued interest is not shown). Status counts (late / in recovery) are what to monitor on the platform.
"""
import argparse, csv, datetime as dt, os, sys

COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']


def pick(r, *names):
    for n in names:
        if n in r and r[n] != '':
            return r[n]
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('projects'); ap.add_argument('summary'); ap.add_argument('--out', default='data/index'); ap.add_argument('--asof', default=dt.date.today().isoformat())
    ap.add_argument('--ccy', default=None); ap.add_argument('--owner', default='')
    a = ap.parse_args()
    P = list(csv.DictReader(open(a.projects, encoding='utf-8-sig')))
    SR = list(csv.DictReader(open(a.summary, encoding='utf-8-sig')))
    S = {r['key']: r['value'] for r in SR}
    ccy = (a.ccy or next((r.get('unit') for r in SR if r['key'] == 'total_value' and r.get('unit')), None) or 'CZK').upper()
    f = lambda k, d=None: float(S[k]) if k in S and S[k] != '' else d
    asof = a.asof
    base = dict(platform='investown', account='Investown', portfolio_type='', country='CZ', native_ccy=ccy, report_ccy=ccy, valuation_date=asof, owner=a.owner)
    rows, item_sum = [], 0.0
    for r in P:
        v = float(pick(r, 'my_investment', 'my_investment_czk')); item_sum += v
        y = pick(r, 'paid_yields', 'paid_yields_czk') or '0'
        rows.append(dict(base, asset_class='crowdlend_project', instrument_id=r['project'], name=r['project'], status='held', cost=f'{v:.2f}', value=f'{v:.2f}', dividends_net=y,
                         interest_rate_pct=r.get('my_rate_pct', ''), confidence='medium',
                         notes=f"real-estate loan project; status {r.get('status', '')}; max rate {r.get('max_rate_pct', '')}% p.a. (yours {r.get('my_rate_pct', '')}% incl. tier bonus); next payout {r.get('next_payout', '')}; "
                               f"project ends in {r.get('ends_in', '')}; dividends_net = yields paid so far; cost=value=amount invested (assumption: outstanding principal); {r.get('note', '')}"))
    pv, cash = f('portfolio_value'), f('free_money')
    rest = pv - item_sum
    n_active = int(f('active_investments', 0))
    n_rest = n_active - len(P)
    in_ext, in_rec = int(f('in_extension', 0)), int(f('in_recovery', 0))
    if n_rest > 0 or abs(rest) > 0.005:
        rows.append(dict(base, asset_class='crowdlend_project', instrument_id='INVESTOWN_OTHER_ACTIVE', name=f'Other {max(n_rest, 0)} active investments (not itemized)', status='held', cost=f'{rest:.2f}',
                         value=f'{rest:.2f}', confidence='low',
                         notes=f"remainder = portfolio value {pv:,.2f} - itemized {item_sum:,.2f}; includes the {in_ext} project(s) in extension and {in_rec} in recovery that are not itemised; "
                               f"~{S.get('share_recovery_pct', '?')}% of all-time invested volume is in recovery"))
    rows.append(dict(base, asset_class='cash', instrument_id=ccy, symbol=ccy, name='Free money (wallet)', status='held', units_net=f'{cash:.2f}', value=f'{cash:.2f}', confidence='high', notes='wallet; available to invest or withdraw'))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'investown.positions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    tv = f('total_value')
    checks = [(f'portfolio value + free money = total value ({tv:,.2f})', abs(pv + cash - tv) < 0.005),
              ('index rows sum = total value', abs(sum(float(r['value']) for r in rows) - tv) < 0.005),
              (f'repaying + extension + recovery = {n_active} active investments', int(f('repaying_on_time', 0) + in_ext + in_rec) == n_active)]
    shares = [f(k) for k in ('share_repaid_pct', 'share_repaying_pct', 'share_extension_pct', 'share_recovery_pct', 'share_writtenoff_pct')]
    if all(x is not None for x in shares):
        checks.append(('status shares sum to 100 %', abs(sum(shares) - 100) < 0.05))
    if f('paid_month') is not None and f('planned_month') is not None:
        checks.append(('paid this month <= planned', f('paid_month') <= f('planned_month')))
    md = [f"---\nplatform: investown\nsource_type: transcribed app screenshots\nvaluation_date: {asof}\ngenerated: {dt.date.today().isoformat()}\nreport_ccy: {ccy}\npositions_csv: investown.positions.csv\n---\n",
          f"# Investown index\n\nTotal value **{tv:,.2f} {ccy}** = invested portfolio {pv:,.2f} + free money {cash:,.2f}."
          + (f" All-time profit {f('total_profit'):,.2f}." if f('total_profit') is not None else '') + (f" Indicative average yield {S['avg_yield_indicative']} % p.a." if 'avg_yield_indicative' in S else '') + "\n",
          f"\n## Portfolio status ({n_active} active investments)\n| Status | Investments | Share of all-time invested volume |\n|---|---:|---:|\n"
          f"| Repaying on time | {S.get('repaying_on_time', '?')} | {S.get('share_repaying_pct', '-')} % |\n| **Late / extension** | **{in_ext}** | {S.get('share_extension_pct', '-')} % |\n"
          f"| **Recovery / enforcement** | **{in_rec}** | {S.get('share_recovery_pct', '-')} % |\n| Repaid | {int(f('projects_total', n_active)) - n_active} | {S.get('share_repaid_pct', '-')} % |\n| Written off | - | {S.get('share_writtenoff_pct', '-')} % |\n"]
    if in_ext or in_rec:
        md.append(f"\n**Attention:** {in_ext} investment(s) late and {in_rec} in recovery. Investown offers no detailed export, so this platform is tracked at high level; re-check the status counts on each new overview/portfolio screenshot.\n")
    if f('paid_month') is not None:
        md.append(f"\nPaid this month {f('paid_month'):,.2f} of {f('planned_month', 0):,.2f} planned" + (f", of which tier bonuses {f('paid_month_bonuses'):,.2f}" if f('paid_month_bonuses') is not None else '') + '.\n')
    if 'tier' in S:
        md.append(f"Tier **{S['tier']}** (+{S.get('tier_bonus_pct', '?')} % p.a.)" + (f"; {S['to_next_tier']} more invested reaches {S.get('next_tier', 'the next tier')} (+{S.get('next_tier_bonus_pct', '?')} % p.a.)" if 'to_next_tier' in S else '') + '.\n')
    md.append(f"\n## Itemized projects ({len(P)} of {n_active} active seen)\n| Project | Invested | Your rate | Paid yields | Next payout | Ends in |\n|---|---:|---:|---:|---|---|\n")
    for r in P:
        md.append(f"| {r['project']} | {float(pick(r, 'my_investment', 'my_investment_czk')):,.2f} | {r.get('my_rate_pct', '')} % | {pick(r, 'paid_yields', 'paid_yields_czk')} | {r.get('next_payout', '')} | {r.get('ends_in', '')} |\n")
    if n_rest > 0:
        md.append(f"| Other {n_rest} active (not itemized) | {rest:,.2f} | - | - | - | - |\n")
    md.append("\n## Platform notes\n- Czech platform where you lend to real-estate development projects and receive monthly interest; principal returns at project end or on early repayment. Security per loan (company claim): pledge on the real estate, personal guarantees, enforceable notarial registration, pledge on the project company's shares; each project has a rating.\n"
              "- Risks: developer/project default, delays and extensions, real-estate downturn, liquidity (secondary market not guaranteed), platform risk, concentration in one platform.\n- A tier adds a bonus yield on top of the project base rate.\n")
    md.append("\n## Reconciliation\n" + ''.join(f"- {'OK' if ok else 'MISMATCH'}: {n}\n" for n, ok in checks))
    md.append("\n## Caveats\n- High-level tracking only: itemised projects are the ones visible on screen; the rest is one remainder row (value assumed = invested principal; accrued interest not shown).\n"
              "- Status shares are of all-time invested volume (including repaid), not of today's portfolio.\n- Project names are truncated in the app; the rate shown is tier-adjusted.\n- Rebuild: `python3 -I parsers/investown_index.py <projects.csv> <summary.csv> --out data/index`\n")
    open(os.path.join(a.out, 'investown.index.md'), 'w', encoding='utf-8').write(''.join(md))
    for n, ok in checks:
        print('OK ' if ok else 'MISMATCH', n)
    print(f'OK investown: {len(rows)} rows')


if __name__ == '__main__':
    main()

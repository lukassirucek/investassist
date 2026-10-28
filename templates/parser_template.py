#!/usr/bin/env python3
"""Template for a platform parser. Copy to local/parsers/<platform>_index.py (git-ignored) and adapt - see the build-parser skill.

Usage: python3 -I local/parsers/<platform>_index.py <input_file_or_dir> [out_dir=data/index]
Writes <out_dir>/<PLATFORM>.positions.csv and <PLATFORM>.index.md (contract: docs/index-spec.md). Idempotent, no network, stdlib only.
"""
import csv, datetime as dt, glob, os, sys

PLATFORM = 'example_broker'          # lower_snake_case; becomes the file name
OWNER = ''                           # '' = the profile owner; set another name for a child's or partner's account
DELIM, DECIMAL, ENCODING = ';', ',', 'utf-8-sig'
COLS = ['platform', 'account', 'portfolio_type', 'asset_class', 'instrument_id', 'symbol', 'name', 'country', 'status', 'native_ccy', 'units_net', 'units_bought', 'units_sold',
        'n_buys', 'first_buy', 'last_buy', 'report_ccy', 'cost', 'fees', 'realized_pnl', 'dividends_gross', 'dividends_tax', 'dividends_net', 'n_dividends', 'last_dividend',
        'value', 'price', 'price_ccy', 'valuation_date', 'confidence', 'notes', 'owner', 'interest_rate_pct']


def num(x):
    """'1 234,56' -> 1234.56; blank -> None. Adapt DECIMAL for the platform."""
    x = (x or '').strip().replace('\xa0', '').replace(' ', '')
    if not x:
        return None
    x = x.replace('.', '').replace(',', '.') if DECIMAL == ',' else x.replace(',', '')
    return float(x)


def read_rows(path):
    with open(path, encoding=ENCODING, newline='') as fh:
        # TODO: skip preamble lines before the header if the export has them
        return list(csv.DictReader(fh, delimiter=DELIM))


def to_positions(rows, src):
    out = []
    for i, r in enumerate(rows, start=2):
        # TODO map the platform's columns; one dict per position (see docs/index-spec.md for meaning of each column)
        ccy = (r.get('Currency') or '').strip().upper()
        out.append(dict(platform=PLATFORM, asset_class='stock', instrument_id=(r.get('ISIN') or '').strip(), symbol=(r.get('Ticker') or '').strip(),
                        name=(r.get('Name') or '').strip(), status='held', native_ccy=ccy, report_ccy=ccy, units_net=num(r.get('Quantity')),
                        cost=num(r.get('Cost')), value=num(r.get('Market value')), price=num(r.get('Price')), price_ccy=ccy,
                        valuation_date=(r.get('Date') or '').strip(), confidence='high', notes=f'{os.path.basename(src)} row {i}', owner=OWNER))
    return out


def main(inp, out='data/index'):
    files = sorted(glob.glob(os.path.join(inp, '*.csv'))) if os.path.isdir(inp) else [inp]
    pos = [p for f in files for p in to_positions(read_rows(f), f)]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f'{PLATFORM}.positions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore'); w.writeheader()
        for p in pos:
            w.writerow({k: ('' if v is None else v) for k, v in p.items()})
    total = sum(p['value'] or 0 for p in pos)
    vd = max((p['valuation_date'] for p in pos if p['valuation_date']), default='')
    open(os.path.join(out, f'{PLATFORM}.index.md'), 'w', encoding='utf-8').write(
        f'---\nplatform: {PLATFORM}\nsource_type: export ({", ".join(os.path.basename(f) for f in files)})\nvaluation_date: {vd}\ngenerated: {dt.date.today().isoformat()}\n'
        f'positions_csv: {PLATFORM}.positions.csv\n---\n\n# {PLATFORM} index\n\npositions: {len(pos)}; sum of values: {total:,.2f}\n\n'
        '## Reconciliation\nTODO: compare with the total shown by the platform and state the gap.\n\n## Caveats\n- TODO\n')
    print(f'OK {PLATFORM}: {len(pos)} positions, value {total:,.2f}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(*sys.argv[1:3])

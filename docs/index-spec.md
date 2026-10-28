# Platform index format

Every platform becomes two files in `data/index/`, written by a parser (`local/parsers/<platform>_index.py`, see skill `build-parser`) or by `scripts/manual_index.py`:

- `<platform>.positions.csv` - one row per position
- `<platform>.index.md` - front matter (`platform`, `source_type`, `valuation_date`, `generated`, `positions_csv`), totals, a **Reconciliation** section (gap to the total the platform shows), **Caveats**

`scripts/build_master_index.py` concatenates all `*.positions.csv` into `master.positions.csv` and adds `cost_base` / `value_base` in the profile's base currency using `data/fx/fx_latest.csv`.

## Columns of `positions.csv`
| column | meaning |
|---|---|
| platform | lower_snake_case platform id; equals the file name |
| account | account label, numbers masked to the last 4 digits |
| portfolio_type | tax wrapper if the platform holds several (regular / retirement / ISA ...); blank otherwise. Never merged in tax output |
| asset_class | stock, etf, fund, bond, crypto, cash, gold, p2p_loan, crowdlend_project, real_estate, commodity, loan_liability, other |
| instrument_id | ISIN if known, else symbol, else the platform's id; used to match `instruments.csv` |
| symbol, name, country | as the platform shows them (country = issuer/domicile, optional) |
| status | held (default), sold_out, late, default, repaid, converted |
| native_ccy / report_ccy | currency of the instrument / currency of cost and value in this file |
| units_net, units_bought, units_sold, n_buys, first_buy, last_buy | quantities and dates from transactions, when known |
| cost | amount invested (net) in report_ccy |
| fees, realized_pnl | from transactions, when known |
| dividends_gross, dividends_tax, dividends_net, n_dividends, last_dividend | income, when known |
| value | market value in report_ccy at `valuation_date`; blank if unknown (never estimated) |
| price, price_ccy | unit price behind `value`, when known |
| valuation_date | ISO date of the statement or screenshot; drives the staleness flag (35 days) |
| confidence | high (statement/export) / medium (typed, screenshot) / low |
| notes | assumptions, source file + row, caveats |
| owner | blank = the profile owner; another name = separate person, excluded from own totals |
| interest_rate_pct | for loans and P2P: the rate the platform shows |

Rules: blank means unknown; never zero-fill. Rows with `status` sold_out/repaid/converted stay for history and are excluded from totals. A parser re-run must give identical output (idempotent). A platform's index is replaced as a whole when a newer export arrives.

## Other files
- `data/fx/fx_latest.csv`: `ccy,to_base,date` - units of the base currency per 1 unit of `ccy`; write it with `scripts/fx_set.py`.
- `data/reference/instruments.csv`: classification per instrument (`ids|name|class|sector|industry|sub_industry|hq|revenue_regions|raw_materials|themes`); add rows with `scripts/instruments_add.py`.
- `data/ledger/mail_events.csv`: written by `scripts/mail_events.py` (date, source, kind, subject, summary, action, deadline).

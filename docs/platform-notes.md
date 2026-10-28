# Platform notes

What each platform gives you and which tool reads it. Parsers: `parsers/`. Typed templates: `examples/typed/`. No personal data here.

## Parsers included
| Platform | Get the file | Tool |
|---|---|---|
| **Revolut** | App > Invest > Documents/Statements > Consolidated statement (xlsx, whole period). The statement has trades, dividends, crypto but **no market values**: add app screenshots of the list screens (view the images, transcribe to CSV `symbol,name,units_shown,price,price_ccy,value_<ccy>,return_pct,screenshot,asset_class` plus a `CASH_<ccy>` row). App list screens truncate units to 2 decimals; an integer ratio between statement and app units means a split after purchase: confirm, then record it in `--aliases` | `parsers/revolut_index.py` |
| **Portu** | Monthly statement PDF per account (one PDF per account holder). Units and values only: no ISIN, no cost. DIP is a separate account | `parsers/portu_index.py` + manifest CSV `file,owner,portfolio_type,holder_note` |
| **Indigo (Patria Finance)** | Quarterly e-mail "Pravidelný výpis z účtu": save as HTML. Deposit/rebalance/dividend notices arrive as separate mails (`ingest-email`) | `parsers/indigo_index.py` |
| **Raiffeisenbank Investice** | Statement PDF "Výpis z majetkového účtu" per contract (regular and DIP are different contracts). Positions only, no cost | `parsers/raiffeisen_index.py` |
| **Investown** | No export. Screens: overview (total, free money, tier), portfolio (counts by status), my investments (projects). Watch the counts of projects in extension / recovery | `parsers/investown_index.py` |
| **Golden Gate** | Platform shows only the grams REMAINING to complete the current 1 oz brick, not what you hold; payment e-mails give the cash paid | `parsers/golden_gate_index.py` |

## Typed route (no parser needed)
| Platform | Template | What to read from the app |
|---|---|---|
| Zonky Rentiér | `examples/typed/zonky.example.csv` | portfolio value and yield % p.a.; an overview screenshot adds invested/earned |
| Patria Finance brokerage | `patria.example.csv` | app blocks screenshots: type units, the second number (usually the **average purchase price**) and the total (current value); keep regular and DIP rows separate via `portfolio_type` |
| ČSOB Investice | `csob_investice.example.csv` | overview + fund detail: "Celkem investováno" = cost; the app may round units; an entry fee may be excluded from the cost basis |
| Air Bank Investice (My Air) | `airbank_investice.example.csv` | no export: value and gain/loss per row from a photo; cost = value - gain/loss (inference) |
| Physical gold / silver | `physical_gold.example.csv` | grams, a dated price per gram with its source; not a platform |
| Bank balances | `csob_bank.example.csv` | balance notification mails; last 4 digits of the account only; negative = overdraft |

## General hints for platforms without a parser
- **PDF statements:** `pdftotext -layout`; position tables are fixed-width; check units x price = value and sum = statement total.
- **Transaction CSV:** net units = buys - sells per ISIN; cost = net invested; splits show as integer ratios between statement and app units.
- **Robo-advisors:** value and return only, often no cost: keep `cost` blank.
- **Crypto exchanges:** CSV history of buys, sells, converts, staking; transfers between own wallets are not P&L.
- **P2P / crowdlending:** asset_class `p2p_loan` / `crowdlend_project`, `interest_rate_pct`, `status` (late, default), `maturity_date`.
- **Wrappers:** use `portfolio_type` (regular / retirement / ...) so they are never merged in tax output.
Add your own findings to `local/notes.md` (private) or send general ones as a pull request.

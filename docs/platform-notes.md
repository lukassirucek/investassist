# Platform notes

What each platform gives you and which tool reads it. Parsers: `parsers/`. Typed templates: `examples/typed/`. No personal data here.

## Parsers included
| Platform | Get the file | Tool |
|---|---|---|
| **Revolut** | App > Documents > Consolidated statement. Two layouts: **xlsx** (Investment Services only, whole history since the first trade: use this for positions) and **csv v2** (all products incl. Current Accounts pockets, but limited to the chosen period: positions/cost/realised P&L are INCOMPLETE; dividends, crypto, pockets and top-ups are valid). Always export "since opening" for positions. Neither has **market values**: add app screenshots of the list screens (view the images, transcribe to CSV `symbol,name,units_shown,price,price_ccy,value_<ccy>,return_pct,screenshot,asset_class` plus a `CASH_<ccy>` row). App list screens truncate units to 2 decimals; an integer ratio between statement and app units means a split after purchase: confirm, then record it in `--aliases`. The csv holds IBANs and custom pocket names: never copy them into docs, memory or logs | `parsers/revolut_index.py` (`--pockets`, `--allow-partial`) |
| **Portu** | Monthly statement PDF per account (one PDF per account holder). Units and values only: no ISIN, no cost. DIP is a separate account | `parsers/portu_index.py` + manifest CSV `file,owner,portfolio_type,holder_note` |
| **Indigo (Patria Finance)** | Quarterly e-mail "Pravidelný výpis z účtu": save as HTML. Deposit/rebalance/dividend notices arrive as separate mails (`ingest-email`) | `parsers/indigo_index.py` |
| **Raiffeisenbank Investice** | Statement PDF "Výpis z majetkového účtu" per contract (regular and DIP are different contracts). Positions only, no cost | `parsers/raiffeisen_index.py` |
| **Investown** | No export. Screens: overview (total, free money, tier), portfolio (counts by status), my investments (projects). Watch the counts of projects in extension / recovery | `parsers/investown_index.py` |
| **Golden Gate** (iPhone app screenshots work: Komoditní účet and Bitcoinový účet screens carry every figure the parser needs, see `examples/typed/golden_gate_manual.example.csv`) | Platform shows only the grams REMAINING to complete the current 1 oz brick, not what you hold; payment e-mails give the cash paid | `parsers/golden_gate_index.py` |

## Typed route (no parser needed)
| Platform | Template | What to read from the app |
|---|---|---|
| Zonky Rentiér (also a line in the Air Bank app: value + "Aktuální výnos" in CZK; the annual % is not shown there) | `examples/typed/zonky.example.csv` | portfolio value and yield % p.a.; an overview screenshot adds invested/earned |
| Patria Finance brokerage | `patria.example.csv` | app screenshots are readable: view the image, type units, the second number (usually the **average purchase price**) and the total (current value); keep regular and DIP rows separate via `portfolio_type`; confidence medium |
| ČSOB Investice | `csob_investice.example.csv` | overview + fund detail: "Celkem investováno" = cost; the app may round units; an entry fee may be excluded from the cost basis |
| Air Bank Investice (My Air; "Investice do akcií" list screen from the iPhone app: value + gain per row, the rows reconcile to the headline) | `airbank_investice.example.csv` | no export: value and gain/loss per row from a photo; cost = value - gain/loss (inference) |
| Physical gold / silver | `physical_gold.example.csv` | grams, a dated price per gram with its source; not a platform |
| Bank balances (ČSOB) | `csob_bank.example.csv` | balance notification mails **or ČSOB Smart app screenshots** (account list, point-in-time, confidence medium); last 4 digits of the account only; negative = overdraft. A **credit card** shows *available*: used = limit − available, record as `loan_liability` with a negative value. A **business account** (Podnikatelský) is separate: its own `owner` value, excluded from own totals. Money earmarked for someone else in own accounts stays in own totals (note it) |
| Bank balances (Raiffeisenbank app) | `raiffeisen_bank.example.csv` | Raiffeisenbank mobile app screenshots (account list, savings, cards): same rules as ČSOB (last 4 digits, credit card = limit − available as `loan_liability`, business account separate via `owner`). When a bank is added later, earlier reports exclude its cash: say so when comparing totals. Not to be confused with Raiffeisenbank **Investice** (`parsers/raiffeisen_index.py`, statement PDF; app screens are also readable) |

## General hints for platforms without a parser
- **PDF statements:** `pdftotext -layout`; position tables are fixed-width; check units x price = value and sum = statement total.
- **Transaction CSV:** net units = buys - sells per ISIN; cost = net invested; splits show as integer ratios between statement and app units.
- **Robo-advisors:** value and return only, often no cost: keep `cost` blank.
- **Crypto exchanges:** CSV history of buys, sells, converts, staking; transfers between own wallets are not P&L.
- **P2P / crowdlending:** asset_class `p2p_loan` / `crowdlend_project`, `interest_rate_pct`, `status` (late, default), `maturity_date`.
- **Wrappers:** use `portfolio_type` (regular / retirement / ...) so they are never merged in tax output.
Add your own findings to `local/notes.md` (private) or send general ones as a pull request.

## Drive drop zone (Exports folder)
One sub-folder per platform, screenshots and exports inside. Screenshot as-of date = the timestamp in the file name / app (not the day the files were dropped). Processed files are moved into a `processed-YYYYMMDD` sub-folder of the same platform folder (e.g. `processed-20260115`); the ingest skips `processed-*` folders. Portu statements arrive as `Vypis_z_uctu_YYYY_MM.pdf`; Raiffeisen Investing and Portu app screens are accepted as screenshots (medium confidence) when no statement exists yet.

## iPhone app screenshots (Indigo, mBank, Golden Gate, Air Bank)
iPhone screenshots do not block (some Android banking apps do); the status-bar clock gives the time, Drive `createdTime` the day. As-of = that day. Read the image yourself (no OCR), transcribe, reconcile to the app's own headline numbers, medium confidence.
| App / screen | What it gives | How it is stored |
|---|---|---|
| **Air Bank** "Chytrý přehled" (home) | Běžné účty (own labels, incl. foreign-currency accounts and a loan account with "včetně kontokorentu" = balance + overdraft limit: record the balance only), Spoření, the app's own "k dispozici" CZK totals; below: Investice do akcií / Investice Portu / Zonky Rentiér values + "Zainvestováno máte celkem" | bank cash: `airbank_bank` (typed, `examples/typed/airbank_bank.example.csv`, native currencies converted with `data/fx/fx_latest.csv`); stocks list: `airbank` (`examples/typed/airbank_investice.example.csv`); Zonky: `zonky` |
| **Air Bank** "Investice Portu" | the same own Portu portfolios as `portu` (NOT additional): a newer total only | `scripts/marks_index.py` mark on `portu` |
| **mBank** "moje prostředky" | total + tiles účty / spoření (per-account split is behind "ukázat": open it if you want rows) | platform `mbank`, typed, `examples/typed/mbank.example.csv` |
| **Golden Gate** Komoditní účet | Nainvestováno, target, "Celkem naspořeno" (grams gold AND silver; includes bricks already delivered), the brick carousel "Zbývá k dosporení x g / y Kč", Souhrn investic: bricks + grams, average and current price per 1 oz (gold) / per tube of 25 oz (silver) | gold price per gram = remainder CZK / remainder g (equals "Aktuální cena" per oz / 31.1035); platform holds only the open brick; delivered bricks = `physical_gold`; metal the owner has decided to exclude (e.g. silver, bricks held by someone else) is listed in `CLAUDE.local.md` |
| **Golden Gate** Bitcoinový účet | Nainvestováno, target, "Celkem naspořeno" BTC (the balance: use this), Souhrn: BTC (gross = invested / average price, slightly higher), average and current price per BTC, "přeplatek" (overpayment) | `golden_gate` with `btc_account / price_czk` so BTC has a market value |
| **Indigo** Přehled / Portfolio / Aktivita | "Hodnota majetku" (whole CZK), "Změna hodnoty majetku" and "Výnos/ztráta" (the two figures did not reconcile with each other: do not store the P&L), Aktivita > Pohyby: dated list (Vklad peněz z účtu, Poplatek za obhospodařování, Kreditní úrok, Rebalance, Jednorázová investice, Výplata dividendy); dates in Czech, e.g. "Leden 15, 2026" | total: mark on `indigo`; small flows: `data/ledger/patria_indigo_events.csv`; no positions in the app screens (they stay from the quarterly statement) |
Reconciliation seen: Air Bank dashboard "Zainvestováno" = Investice do akcií + Portu + Zonky exactly; stocks list rows sum to the headline and gains sum to the headline gain.

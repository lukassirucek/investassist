---
name: seasonality
description: Compute and report historical seasonal patterns (company, sector, commodity, index) for owned positions, e.g. consumer-staples/QSR weakness autumn-winter and recovery spring-summer; flag when the current calendar window historically matters.
---
Use price history (≥ 10y where available; state N years). Compute monthly avg return, hit rate (% positive years), median, and dispersion vs the benchmark; strip market beta (excess vs benchmark). Store in `data/seasonality/<id>.json`. Report only patterns with hit rate ≥ 65% and N ≥ 8, and always show N and hit rate. Add fundamental explanation if known (earnings cycle, demand, weather, tax-loss selling, dividend timing). Label `HISTORICAL PATTERN`, not a forecast. Also: upcoming-window digest (next 30d) per position and commodity (gold Jan-Feb strength, heating oil/natgas winter, etc. - verify with data, don't assume).
Scripts: put reusable Python in `scripts/seasonality.py` (yfinance or other source must be confirmed available; cite source).

---
name: news-companies
description: Daily news and filings search for every owned company/ETF/crypto, using aliases from the exposure map. Covers earnings dates, guidance, M&A, litigation, management changes, analyst actions, abnormal price moves.
---
For each position (weight-ordered): WebSearch `"<alias>" news` last 48h (standard mode; extended only for large/unclear events). Check upcoming earnings/dividend/ex-dates in the next 14d. Flag abnormal move (|1d| >= 5% or >= 2.5 sigma) with/without news. Output only material items; drop PR fluff and duplicates; each with URL + date + FACT/INFERENCE split. Include supplier/customer/competitor news only when linked via exposure map.

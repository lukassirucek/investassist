---
name: alt-invest-watch
description: Monitor loan, crowdfunding and P2P platform positions - delays, defaults, maturities, concentration, platform and regulatory news. Use weekly when the portfolio holds such platforms.
---
Source: rows with asset_class `p2p_loan`, `crowdlend_project`, `loan` in `data/index/master.positions.csv` plus `data/ledger/mail_events.csv`. List items with status other than held, payment delays (days), maturities in the next 90 days, extensions, rate changes; platform concentration as % of the whole portfolio and of the alternative sleeve; weighted yield vs risk grade; developer/collateral concentration; liquidity ladder (when cash returns). Search platform and developer news and the home country's regulator / EU crowdfunding rules (ESMA) and the insolvency register. A delay beyond 30 days or a default is critical per `config/alerts.yaml`.

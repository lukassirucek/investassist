---
name: housing-watch
description: Monitor housing markets and rates relevant to real-estate-linked holdings (crowdlending projects, own mortgage, REIT/ETF exposure) - prices, transactions, permits, mortgage rates, regulation. Use weekly when such holdings exist.
---
Scope from `config/profile.yaml` `country` and the exposure map (collateral locations, REITs/ETFs). Home market first: regional price per m^2 from the national statistics office, central bank and big listing indices; mortgage rates and volumes; central-bank rate decisions; building permits; zoning/planning law changes. International only if ETFs/REITs are owned. Tie to project collateral, LTV, developer exposure and the owner's own mortgage fixation end (flag 6 months ahead with the rate outlook). Weekly depth; daily only for changes.

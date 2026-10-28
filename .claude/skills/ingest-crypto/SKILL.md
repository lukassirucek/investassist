---
name: ingest-crypto
description: Parse cryptocurrency exports (exchange CSVs, wallet exports, app screenshots) into the platform index.
---
First use: ask which exchanges and wallets are used and record them in `config/sources.yaml`. Exchange CSV -> `build-parser`; screenshots or typed balances -> `ingest-manual` with asset_class `crypto`. Normalise buy/sell/convert/staking/rewards/fees/transfers (transfers between own wallets are not P&L). Holdings = cumulative balance per asset; price from a dated public source with a citation; flag assets without a reliable price. Keep the chain/network for hazard and regulatory notes. Never store seed phrases or API secrets; if one appears in a file, stop and tell the user.

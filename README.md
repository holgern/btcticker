# btcticker

Bitcoin ticker rendering with a provider-based price backend.

## Config

`btcticker` now defaults to the `pyccxt` backend. The main price settings are:

```ini
[Main]
price_provider = pyccxt
exchange = kraken
symbol = BTC/EUR
usd_symbol = BTC/USD
ccxt_timeout = 30000
price_refresh_seconds = 10
```

If `symbol` is empty, `btcticker` derives it from `fiat` as `BTC/<FIAT>`.

Legacy `price_service` configs are no longer supported. Migrate them to
`price_provider=pyccxt` plus explicit `exchange`, `symbol`, and `usd_symbol` values.

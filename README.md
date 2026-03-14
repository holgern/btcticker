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

## CLI Config Selection

Config selection flags work globally for all commands:

```bash
btcticker --config my_config.ini text
btcticker --config my_config.ini image --output ticker.png
btcticker --config my_config.ini download
btcticker --config my_config.ini config edit
```

You can also use:

```bash
btcticker --local text
btcticker --global image
```

Only one of `--config`, `--local`, or `--global` may be used at a time.

For compatibility, command-local forms still work too:

```bash
btcticker text --config my_config.ini
btcticker image --local
btcticker config --global
```

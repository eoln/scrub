# scrub
Glassnode API scrapping utility

## setup local development:
- dev deps 
```bash
pip3 install virtualenv wheel setuptools twine
```
- clone repo
- go to working dir 
```bash
cd scrub
```
- setup pyton venv 
```bash
virtualenv venv
```
- initialise venv 
```bash
source venv/bin/activate
```
- install deps & build dev version in venv 
```bash
python setup.py develop
```
- test run cli command 
```bash
scrub
```

## glassnode api key
put api key into envvar
```bash
export GLASSNODE_API_KEY=<your_api_key>
```

## scrub commands
```bash
> scrub --help

Usage: scrub [OPTIONS] COMMAND [ARGS]...

Options:
  -g, --apikey TEXT  glassnode api key  [required]
  -o, --outdir TEXT  folder where data is dumped  [default: ./data; required]
  --help             Show this message and exit.

Commands:
  endpoints
  scrape
```
### scrub endpoints
> Generates endpoints to be fetched by `scrub scrap`
```bash
> scrub endpoints --help

Usage: scrub endpoints [OPTIONS]

Options:
  -a, --assets TEXT    digital asset code: BTC, ETH, ...  [default: *;
                       required]
  -t, --tiers INTEGER  tier: 1, 2, 3  [default: 0; required]
  -p, --path TEXT      filter by path specified as regular expression
                       [default: *; required]
  --help               Show this message and exit.
```

### scrub scrape
> fetch data specified in `data/endpoints.json` and store them into `csv` files into `data` folder
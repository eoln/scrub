from array import array
from asyncio import Queue, create_task, gather, sleep
import asyncio
import asyncclick as click
import aiohttp
from aiofiles import open
from aiofiles.os import makedirs
import logging
import json
import random
import re
from os.path import isfile

# setup logging
logging.basicConfig(filename='scrub.log', encoding='utf-8', level=logging.DEBUG)
       

config = {
  'host': 'https://api.glassnode.com',
  'session': None,
  'resolutions': ['10m', '1h', '24h', '1w', '1month']
}

# fetch data from given path
async def fetch(path: str, session: aiohttp.ClientSession, **kwargs) -> any: 
  url = f"{config['host']}{path}"
  #response = await session.request(method='get', url=url, allow_redirects=True, timeout=1800, **kwargs)
  response = await session.request(method='get', url=url, allow_redirects=True, **kwargs)
  response.raise_for_status()
  logging.info(F"GET {url}")
  return response

# fetch endpoints data 
async def fetch_endpoints() -> array:
  async with aiohttp.ClientSession(headers={'x-api-key': config['apikey']}) as session:
    resp = await fetch('/v2/metrics/endpoints', session)
    return await resp.json()

# predicate return true if symbol is on asset list
def has_any_asset(assets: array, asset: dict) -> bool:
  return asset['symbol'] in assets

# filters endpints by assets
def filter_by_assets(endpoints: array, assets: array) -> array:
  result = []
  for e in endpoints:
    filtered_assets = [a for a in filter(lambda x: has_any_asset(assets, x), e['assets'])]
    if(not len(filtered_assets)): 
      continue
    else:
      e['assets'] = filtered_assets
    result.append(e)
  return result

# filters endpoints by tier level
def filter_by_tiers(endpoints: array, tiers: array) -> array:
  return [e for e in filter(lambda x: x['tier'] in tiers, endpoints)]

# filters endpoints by matchin path with regular expression
def filter_by_path(endpoints: array, path: str) -> array:
  r = re.compile(path)
  return [e for e in filter(lambda x: r.match(x['path']), endpoints)]

# store response into file
async def store(file: str, response: any) -> None:
  is_stream = hasattr(response, 'content')
  mode = 'wb' if is_stream else 'wt'
  file = f"{config['outdir']}/{file}"
  async with open(file=file, mode=mode) as f:
    if is_stream:
      async for chunk in response.content.iter_chunked(4096):
        await f.write(chunk)
    else:
      await f.write(response)
    logging.info(F"STORE {file}")

def exists(file: str) -> bool:
  path = f"{config['outdir']}/{file}"
  return isfile(path)
  
# retrieve data from file
async def retrieve(file: str) -> str:
  async with open(file=f"{config['outdir']}/{file}", mode='rt') as f:
    return await f.read()

@click.group()
@click.option('-g','--apikey', required=True, envvar='GLASSNODE_API_KEY', help='glassnode api key')
@click.option('-o', '--outdir', required=True, default='./data', show_default=True, help='folder where data is dumped')
async def cli(apikey, outdir):
  # store config
  config['outdir'] = outdir
  config['apikey'] = apikey

  # prepare data directory if not exists
  await makedirs(outdir, mode=0o777, exist_ok=True)
  
# retrieve the endpoints specification
@cli.command()
@click.option('-a', '--assets', required=True, default=['*'], show_default=True, multiple=True, help='digital asset code: BTC, ETH, ...')
@click.option('-t', '--tiers', required=True, default=[0], type=int, show_default=True, multiple=True, help='tier: 1, 2, 3')
@click.option('-p', '--path', required=True, default='*', show_default=True, help='filter by path specified as regular expression')
async def endpoints(assets, tiers, path):
  endpoints = await fetch_endpoints()
  if(not '*' in assets):
    logging.info(f"ASSETS ${assets}")
    endpoints = filter_by_assets(endpoints, assets)
  if(not 0 in tiers):
    logging.info(f"TIERS ${tiers}")
    endpoints = filter_by_tiers(endpoints, tiers)
  if(path != '*'):
    logging.info(f"PATH ${path}")
    endpoints = filter_by_path(endpoints, path)
  await store('endpoints.json', json.dumps(endpoints))

def smallest_resolution(resolutions: array) -> str: 
  conf_res = config['resolutions']
  for r in conf_res:
    if r in resolutions:
      return r
  return resolutions[0]


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n): 
        yield l[i:i + n]

async def producer(queue: Queue, endpoints: array) -> None:
  messages = []
  for e in endpoints:
    path = e['path']
    for a in e['assets']:
      symbol = a['symbol']
      resolution = smallest_resolution(e['resolutions'])
      messages.append((path, symbol, resolution))
  logging.info(f"TODO {len(messages)} items to fetch")
  
  # shuffling messages to distribute load over endpoints
  random.shuffle(messages)
  # push messages to queue in batches
  for batch in divide_chunks(messages, 8):
    for b in batch:
      await queue.put(b)
    #await queue.join()
    await sleep(0.5)


async def worker(n: int, queue: Queue, session: aiohttp.ClientSession) -> None:
  while True:
    (path, symbol, resolution) = await queue.get()
    try:
      file = f"{path.replace('/', '-')}.{symbol}.{resolution}.csv"
      if(exists(file)):
        logging.info(f"SKIPPED ${(path, symbol, resolution)}")
      else:
        logging.info(f"PROCESS ${(path, symbol, resolution)}")
        res_arg =  f"&i={resolution}" if resolution else ''
        response = await fetch(f"{path}?a={symbol}{res_arg}&f=csv", session)
        await store(file, response)
    except (
      aiohttp.ClientError,
      aiohttp.http_exceptions.HttpProcessingError,
    ) as e:
      logging.error(
        f"{path}.{symbol}.{resolution}, {getattr(e, 'status', 'no-status')} {getattr(e, 'message', 'no-message')}" 
      )
      # let try again
      # await queue.put((path, symbol, resolution))
      await sleep(1)
    except asyncio.exceptions.TimeoutError:
      logging.error(
        f"{path}.{symbol}.{resolution}, TimeoutError"
      )
      # let try again
      await sleep(1)
      await queue.put((path, symbol, resolution))
    except Exception as e:
       logging.error(
        f"{path}.{symbol}.{resolution}, Exception", e
       )
       await sleep(1)

    await sleep(0.3)
    queue.task_done()

# scrape data
@cli.command()
async def scrape():
  num_workers = 18
  endpoints = json.loads(await retrieve('endpoints.json'))
  if(not len(endpoints)):
    logging.info('no endpoints')
    return

  queue = Queue()
  # session_timeout = aiohttp.ClientTimeout(total=None,sock_connect=1800,sock_read=1800)
  #async with aiohttp.ClientSession(headers={'x-api-key': config['apikey']}, timeout=session_timeout) as session:
  async with aiohttp.ClientSession(headers={'x-api-key': config['apikey']}) as session:
    workers = [create_task(worker(n, queue, session)) for n in range(num_workers)]
    producers = [create_task(producer(queue, endpoints))]
    await gather(*producers)
    await queue.join()  # Implicitly awaits consumers, too
    for w in workers:
        w.cancel()
if __name__ == '__main__':
    cli(_anyio_backend="asyncio")
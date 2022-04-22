import anyio
import asyncclick as click

config = {'apikey':''}
@click.group()
@click.option('--apikey', envvar='GLASSNODE_API_KEY')
async def cli(apikey):
  config['apikey'] = apikey

@cli.command()
async def endpoints():
  click.echo(f"apikey:{config['apikey']}")
  click.echo('endpoints')



if __name__ == '__main__':
    cli(_asyncio_backend="asyncio")
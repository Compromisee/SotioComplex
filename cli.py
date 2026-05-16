import click, requests, json

API = "http://localhost:5000"

@click.group()
def cli(): pass

@cli.command()
@click.option('--preset', default='tech')
@click.option('--max', 'max_n', default=3)
@click.option('--shorts/--landscape', default=True)
@click.option('--style', default='social_hook')
def run(preset, max_n, shorts, style):
    """htmldash run --preset tech --max 5 --shorts"""
    presets = requests.get(f"{API}/api/bootstrap").json()['presets']
    sites = presets['source_presets'].get(preset, [])
    click.echo(f"→ Scraping {len(sites)} sites")
    requests.post(f"{API}/api/scrape-themes", json={"sites":sites})
    import time; time.sleep(5)
    themes = requests.get(f"{API}/api/bootstrap").json()  # poll
    click.echo("→ Run via dashboard UI to complete pipeline")

@cli.command()
def cache_clear():
    requests.post(f"{API}/api/cache/clear")
    click.echo("✓ Cache cleared")

@cli.command()
def health():
    r = requests.get(f"{API}/api/source-health").json()
    for s in r: click.echo(f"{s['site']:40} score={s['score']}%")

if __name__ == '__main__':
    cli()
# src/honeytrail/cli.py
import asyncio

import typer

from honeytrail.server import run

app = typer.Typer()


@app.command()
def main() -> None:
    """Run the Honey-Trail MCP stdio server."""
    asyncio.run(run())


if __name__ == "__main__":
    app()

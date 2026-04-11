from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from honeyhex.mesh.outbox import enqueue_pr, list_pending, sync_outbox


def register_outbox_commands(app: typer.Typer) -> None:
    ob = typer.Typer(help="Queue PR intents offline under .honeyhex/outbox/pending/.")

    @ob.command("enqueue")
    def enqueue_cmd(
        source: str = typer.Option(
            ...,
            "--source",
            help="Source agent id (this cell).",
        ),
        target: str = typer.Option(
            ...,
            "--target",
            help="Target agent id for review.",
        ),
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        swarm_id: Annotated[str, typer.Option("--swarm")] = "default",
        title: Annotated[str, typer.Option("--title")] = "",
    ) -> None:
        """Queue a PR payload locally (same fields as `hex push`)."""
        root = (cell or Path.cwd()).resolve()
        item = enqueue_pr(
            root,
            source=source,
            target=target,
            swarm_id=swarm_id,
            title=title,
        )
        typer.echo(json.dumps({"enqueued": item.model_dump()}, indent=2))

    @ob.command("list")
    def list_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """List pending outbox items."""
        root = (cell or Path.cwd()).resolve()
        items = [p.model_dump() for p in list_pending(root)]
        typer.echo(json.dumps(items, indent=2))

    @ob.command("sync")
    def ob_sync_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        refresh_head: Annotated[
            bool,
            typer.Option(
                "--refresh-head",
                help="Replace stored head with current HEAD before POST.",
            ),
        ] = False,
    ) -> None:
        """Flush pending items to the registry (runs `pre-push` per item)."""
        root = (cell or Path.cwd()).resolve()
        result = sync_outbox(root, refresh_head=refresh_head)
        typer.echo(json.dumps(result, indent=2))

    app.add_typer(ob, name="outbox")

    @app.command("sync")
    def sync_top_level(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        refresh_head: Annotated[
            bool,
            typer.Option(
                "--refresh-head",
                help="Replace stored head with current HEAD before POST.",
            ),
        ] = False,
    ) -> None:
        """Alias for `hex outbox sync` — POST queued PRs to the registry."""
        root = (cell or Path.cwd()).resolve()
        result = sync_outbox(root, refresh_head=refresh_head)
        typer.echo(json.dumps(result, indent=2))

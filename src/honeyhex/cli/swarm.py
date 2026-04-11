from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from honeyhex.daemon.config import DaemonConfig
from honeyhex.mesh.publish import announce_truth_commit
from honeyhex.mesh.registry_pr import post_pr_to_registry, registry_url


def _httpx_mod() -> Any:
    try:
        import httpx
    except ImportError as e:
        msg = "Install registry extras: pip install 'honeyhex[registry]'"
        raise ImportError(msg) from e
    return httpx


def register_swarm_commands(app: typer.Typer) -> None:
    @app.command("status")
    def status_cmd(
        swarm_id: Annotated[
            str,
            typer.Option("--swarm", help="Swarm id."),
        ] = "default",
    ) -> None:
        """Show registry + agent HEADs + open PRs (Phase 6)."""
        try:
            httpx = _httpx_mod()
        except ImportError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from None
        url = f"{registry_url()}/api/v1/status"
        r = httpx.get(url, params={"swarm_id": swarm_id}, timeout=30.0)
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))

    @app.command("push")
    def push_cmd(
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
        """Open an inter-agent PR in the registry (immediate POST; see hex outbox)."""
        root = (cell or Path.cwd()).resolve()
        try:
            out = post_pr_to_registry(
                root,
                source=source,
                target=target,
                swarm_id=swarm_id,
                title=title or f"{source} -> {target}",
            )
        except (RuntimeError, ImportError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps(out, indent=2))

    @app.command("vote")
    def vote_cmd(
        pr_id: str = typer.Option(
            ...,
            "--pr",
            help="Pull request id.",
        ),
        validator: str = typer.Option(
            ...,
            "--validator",
            help="Validator agent id.",
        ),
        approve: Annotated[bool, typer.Option("--approve/--reject")] = True,
    ) -> None:
        """Cast a validator vote on an open PR."""
        try:
            httpx = _httpx_mod()
        except ImportError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from None
        url = f"{registry_url()}/api/v1/prs/{pr_id}/votes"
        r = httpx.post(
            url,
            json={"validator_id": validator, "approved": approve},
            timeout=30.0,
        )
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))

    @app.command("merge-quorum")
    def merge_quorum_cmd(
        pr_id: str = typer.Option(
            ...,
            "--pr",
            help="Pull request id.",
        ),
    ) -> None:
        """Merge a PR if validator quorum is satisfied (Phase 6)."""
        try:
            httpx = _httpx_mod()
        except ImportError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from None
        url = f"{registry_url()}/api/v1/prs/{pr_id}/merge"
        r = httpx.post(url, timeout=30.0)
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))

    @app.command("rebase-global")
    def rebase_global_cmd(
        commit: str = typer.Option(
            ...,
            "--commit",
            help="Truth commit to broadcast.",
        ),
        redis_url: Annotated[str | None, typer.Option("--redis-url")] = None,
        channel: Annotated[str | None, typer.Option("--channel")] = None,
    ) -> None:
        """Publish a global truth commit on Redis for daemons/agents (Phase 6)."""
        cfg = DaemonConfig.from_env()
        url = redis_url or cfg.redis_url
        ch = channel or cfg.channel
        try:
            announce_truth_commit(url, ch, commit)
        except ImportError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from None
        typer.echo(json.dumps({"truth_commit": commit, "channel": ch}, indent=2))

    @app.command("db-url")
    def db_url_cmd() -> None:
        """Print resolved HONEYHEX_DATABASE_URL (for debugging)."""
        from honeyhex.registry.db import database_url

        typer.echo(database_url())

from __future__ import annotations

import asyncio
import json
import signal
import threading
import time
from pathlib import Path
from typing import Annotated, Any

import typer

from honeyhex.branching.git_ops import (
    checkout_new_branch,
    cherry_pick,
    rebase_interactive_drop,
)
from honeyhex.branching.shadow import run_dual_shell_commands
from honeyhex.cli.llm_cmds import register_llm_commands
from honeyhex.cli.outbox_cli import register_outbox_commands
from honeyhex.cli.porcelain import register_porcelain_commands
from honeyhex.cli.swarm import register_swarm_commands
from honeyhex.commit.manager import CommitManager
from honeyhex.commit.models import StateDiff
from honeyhex.daemon.config import DaemonConfig
from honeyhex.daemon.service import HiveDaemon
from honeyhex.mesh.publish import announce_head, read_head_sha

app = typer.Typer(
    name="hex",
    help="HoneyHex — distributed ledger of intelligence for agent cells.",
    no_args_is_help=True,
)

daemon_app = typer.Typer(help="Hive-Daemon (Redis Pub/Sub).")
app.add_typer(daemon_app, name="daemon")

register_swarm_commands(app)
register_porcelain_commands(app)
register_outbox_commands(app)
register_llm_commands(app)


@app.callback()
def _root() -> None:
    """HoneyHex CLI root."""


@app.command("commit")
def commit_cmd(
    message: str = typer.Option(
        ...,
        "-m",
        "--message",
        help="Internal monologue (commit message).",
    ),
    prompt: Annotated[str, typer.Option("--prompt", help="Prompt snapshot.")] = "",
    rag_context: Annotated[
        str,
        typer.Option("--rag-context", help="RAG context."),
    ] = "",
    scratchpad: Annotated[str, typer.Option("--scratchpad", help="Scratchpad.")] = "",
    tools_json: Annotated[
        str | None,
        typer.Option("--tools-json", help="Tool outputs as a JSON array."),
    ] = None,
    cell: Annotated[
        Path | None,
        typer.Option("--cell", help="Agent cell root (default: cwd)."),
    ] = None,
    payload_file: Annotated[
        Path | None,
        typer.Option(
            "--payload-file",
            help="JSON file: prompt, rag_context, scratchpad, tool_outputs.",
        ),
    ] = None,
) -> None:
    """Snapshot the current Think-to-Act cycle into `.honeyhex/`."""
    root = (cell or Path.cwd()).resolve()
    if payload_file is not None:
        data = json.loads(payload_file.read_text(encoding="utf-8"))
        diff = StateDiff.model_validate(data)
    else:
        tool_outputs: list[dict[str, Any]] = []
        if tools_json:
            parsed = json.loads(tools_json)
            if not isinstance(parsed, list):
                raise typer.BadParameter("--tools-json must be a JSON array")
            tool_outputs = [x for x in parsed if isinstance(x, dict)]
            if len(tool_outputs) != len(parsed):
                raise typer.BadParameter("--tools-json must be a JSON array of objects")
        diff = StateDiff(
            prompt=prompt,
            rag_context=rag_context,
            scratchpad=scratchpad,
            tool_outputs=tool_outputs,
        )

    manager = CommitManager(root)
    thought = manager.commit(message, diff)
    typer.echo(thought.model_dump_json(indent=2))


@app.command("checkout")
def checkout_cmd(
    branch: Annotated[str, typer.Argument(help="Branch name.")],
    new_branch: Annotated[
        bool,
        typer.Option("-b", "--branch", help="Create and switch to a new branch."),
    ] = False,
    cell: Annotated[
        Path | None,
        typer.Option("--cell", help="Agent cell root (default: cwd)."),
    ] = None,
) -> None:
    """Switch or create branches in `.honeyhex` (Git checkout / checkout -b)."""
    root = (cell or Path.cwd()).resolve()
    if not new_branch:
        typer.echo("Use -b/--branch to create a new branch.", err=True)
        raise typer.Exit(code=2)
    checkout_new_branch(root, branch)
    typer.echo(json.dumps({"branch": branch, "cell": str(root)}, indent=2))


@app.command("cherry-pick")
def cherry_pick_cmd(
    commit_sha: Annotated[str, typer.Argument(help="Commit hash to cherry-pick.")],
    cell: Annotated[
        Path | None,
        typer.Option("--cell", help="Agent cell root (default: cwd)."),
    ] = None,
) -> None:
    """Cherry-pick a commit onto the current `.honeyhex` branch."""
    root = (cell or Path.cwd()).resolve()
    new_head = cherry_pick(root, commit_sha)
    typer.echo(json.dumps({"head": new_head}, indent=2))


@app.command("rebase-interactive")
def rebase_interactive_cmd(
    onto: str = typer.Option(
        ...,
        "--onto",
        help="New base (ancestor of HEAD).",
    ),
    drop: str | None = typer.Option(
        None,
        "--drop",
        help="Comma-separated commit hashes to drop from (onto..HEAD].",
    ),
    fix_message: str | None = typer.Option(
        None,
        "--fix-message",
        help="Optional fix prompt written after rebase.",
    ),
    cell: Annotated[
        Path | None,
        typer.Option("--cell", help="Agent cell root (default: cwd)."),
    ] = None,
) -> None:
    """
    Drop listed commits between onto and HEAD, replay the rest (Git cherry-picks).
    Optionally records a fix prompt under thoughts/fix_prompt.txt and commits it.
    """
    root = (cell or Path.cwd()).resolve()
    drops = [s.strip() for s in drop.split(",")] if drop else []
    try:
        head = rebase_interactive_drop(
            root,
            onto,
            drops,
            fix_message=fix_message,
        )
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    typer.echo(json.dumps({"head": head}, indent=2))


@app.command("shadow")
def shadow_cmd(
    left_cmd: str = typer.Option(
        ...,
        "--left-cmd",
        help="Left shell command.",
    ),
    right_cmd: str = typer.Option(
        ...,
        "--right-cmd",
        help="Right shell command.",
    ),
) -> None:
    """Run two shell commands; first successful exit wins (shadow-branch race)."""

    async def _run() -> None:
        result = await run_dual_shell_commands(left_cmd, right_cmd)
        typer.echo(
            json.dumps(
                {
                    "winner": result.winner,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            )
        )

    asyncio.run(_run())


@daemon_app.command("run")
def daemon_run_cmd(
    redis_url: Annotated[
        str | None,
        typer.Option("--redis-url", help="Override HONEYHEX_REDIS_URL."),
    ] = None,
    channel: Annotated[
        str | None,
        typer.Option("--channel", help="Override HONEYHEX_CHANNEL."),
    ] = None,
) -> None:
    """Run the Hive-Daemon: subscribe to Redis and track swarm HEAD / truth events."""
    cfg = DaemonConfig.from_env()
    if redis_url is not None:
        cfg = DaemonConfig(redis_url=redis_url, channel=cfg.channel)
    if channel is not None:
        cfg = DaemonConfig(redis_url=cfg.redis_url, channel=channel)

    shutdown = threading.Event()

    def handle_sigint(_sig: int, _frame: object) -> None:
        shutdown.set()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        daemon = HiveDaemon(cfg)
        daemon.start()
    except ImportError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(
        json.dumps(
            {
                "status": "running",
                "redis_url": cfg.redis_url,
                "channel": cfg.channel,
            },
            indent=2,
        )
    )
    try:
        while not shutdown.is_set():
            time.sleep(0.2)
    finally:
        daemon.stop()
        typer.echo(json.dumps({"status": "stopped"}, indent=2))


@app.command("publish-head")
def publish_head_cmd(
    agent: str = typer.Option(
        ...,
        "--agent",
        help="Agent id for this cell.",
    ),
    cell: Annotated[
        Path | None,
        typer.Option("--cell", help="Agent cell root (default: cwd)."),
    ] = None,
    redis_url: Annotated[
        str | None,
        typer.Option("--redis-url", help="Override HONEYHEX_REDIS_URL."),
    ] = None,
    channel: Annotated[
        str | None,
        typer.Option("--channel", help="Override HONEYHEX_CHANNEL."),
    ] = None,
) -> None:
    """Publish this cell's `.honeyhex` HEAD to the mesh (Redis Pub/Sub)."""
    cfg = DaemonConfig.from_env()
    url = redis_url or cfg.redis_url
    ch = channel or cfg.channel
    root = (cell or Path.cwd()).resolve()
    head = read_head_sha(root)
    try:
        announce_head(url, ch, agent, head)
    except ImportError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(json.dumps({"agent": agent, "head": head, "channel": ch}, indent=2))


def main() -> None:
    app()


if __name__ == "__main__":
    main()

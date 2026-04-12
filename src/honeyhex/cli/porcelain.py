from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from git.exc import GitCommandError

from honeyhex.adoption.timeutil import parse_iso_datetime
from honeyhex.branching.git_ops import create_lightweight_tag, merge_branch
from honeyhex.bundle.io import create_bundle, replay_bundle
from honeyhex.cell.hooks import HookContext, echo_hook_output, run_named_hook
from honeyhex.cell.remotes import (
    add_remote,
    fetch_remote,
    load_swarm_remotes,
    pull_remote,
    remove_remote,
)
from honeyhex.cell.scaffold import init_cell
from honeyhex.inspect.core import (
    diff_as_json,
    diff_snapshots,
    ensure_repo,
    format_log_text,
    git_blame_as_json,
    git_blame_snapshot,
    git_log_graph,
    git_reflog,
    iter_log,
    log_as_json,
    show_revision,
)
from honeyhex.ledger.git_store import HoneyHexLedger
from honeyhex.signing.hmac_sign import sign_commit, verify_commit


def register_porcelain_commands(app: typer.Typer) -> None:
    @app.command("log")
    def log_cmd(
        n: Annotated[
            int | None,
            typer.Option("--max-count", "-n", help="Limit number of commits."),
        ] = None,
        since: Annotated[
            str | None,
            typer.Option(
                "--since",
                help="Include commits at/after UTC date or ISO time.",
            ),
        ] = None,
        until: Annotated[
            str | None,
            typer.Option(
                "--until",
                help="Include commits at/before UTC date or ISO time.",
            ),
        ] = None,
        grep: Annotated[
            str | None,
            typer.Option("--grep", help="Substring filter on commit message."),
        ] = None,
        after_tag: Annotated[
            str | None,
            typer.Option(
                "--after-tag",
                help="Commits in git range tag..HEAD (see git rev-list).",
            ),
        ] = None,
        oneline: Annotated[
            bool,
            typer.Option("--oneline", help="One line per commit."),
        ] = False,
        graph: Annotated[
            bool,
            typer.Option("--graph", help="Show ASCII graph (Git log --graph)."),
        ] = False,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        as_json: Annotated[
            bool,
            typer.Option("--json", help="Machine-readable JSON array."),
        ] = False,
    ) -> None:
        """List thought-commits in `.honeyhex` (newest first)."""
        root = (cell or Path.cwd()).resolve()
        since_dt = parse_iso_datetime(since)
        until_dt = parse_iso_datetime(until)
        has_filters = any(
            x is not None for x in (since_dt, until_dt, grep, after_tag)
        )
        if graph and has_filters:
            typer.echo(
                "hex log: --graph cannot be combined with "
                "--since/--until/--grep/--after-tag",
                err=True,
            )
            raise typer.Exit(code=2)
        if graph:
            ensure_repo(root)
            text = git_log_graph(root, n)
            typer.echo(text, nl=False)
            return
        ensure_repo(root)
        if as_json:
            typer.echo(
                log_as_json(
                    root,
                    max_count=n,
                    since=since_dt,
                    until=until_dt,
                    message_grep=grep,
                    after_tag=after_tag,
                ),
            )
            return
        entries = iter_log(
            root,
            max_count=n,
            since=since_dt,
            until=until_dt,
            message_grep=grep,
            after_tag=after_tag,
        )
        typer.echo(format_log_text(entries, oneline=oneline), nl=bool(entries))

    @app.command("show")
    def show_cmd(
        rev: Annotated[
            str | None,
            typer.Argument(help="Revision (default: HEAD)."),
        ] = None,
        as_json: Annotated[
            bool,
            typer.Option("--json", help="Machine-readable JSON."),
        ] = False,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Show one thought-commit (message + snapshot)."""
        root = (cell or Path.cwd()).resolve()
        r = rev or "HEAD"
        ensure_repo(root)
        typer.echo(show_revision(root, r, as_json=as_json))

    @app.command("diff")
    def diff_cmd(
        rev_a: Annotated[
            str | None,
            typer.Argument(help="Older revision (omit with rev_b for default range)."),
        ] = None,
        rev_b: Annotated[
            str | None,
            typer.Argument(help="Newer revision (default: HEAD)."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        as_json: Annotated[
            bool,
            typer.Option("--json", help="JSON with unified diff text."),
        ] = False,
    ) -> None:
        """Diff thoughts/snapshot.json between revisions (default: HEAD~1 vs HEAD)."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        try:
            if as_json:
                typer.echo(diff_as_json(root, rev_a, rev_b))
                return
            out = diff_snapshots(root, rev_a, rev_b)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(out, nl=bool(out))

    @app.command("remote")
    def remote_cmd(
        action: Annotated[str, typer.Argument(help="add | list | remove")],
        name: Annotated[str | None, typer.Argument(help="Remote name.")] = None,
        path: Annotated[
            str | None,
            typer.Argument(help="Peer cell root or https/git URL (for add)."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Manage swarm peers (local paths) in `.honeyhex/swarm.json`."""
        root = (cell or Path.cwd()).resolve()
        if action == "list":
            swarm = load_swarm_remotes(root)
            typer.echo(json.dumps(swarm.remotes, indent=2))
            return
        if action == "add":
            if not name or path is None:
                typer.echo("usage: hex remote add <name> <path-or-url>", err=True)
                raise typer.Exit(code=2)
            try:
                add_remote(root, name, path)
            except ValueError as e:
                typer.echo(str(e), err=True)
                raise typer.Exit(code=1) from e
            typer.echo(json.dumps({"added": name, "target": path}))
            return
        if action == "remove":
            if not name:
                typer.echo("usage: hex remote remove <name>", err=True)
                raise typer.Exit(code=2)
            try:
                remove_remote(root, name)
            except KeyError as e:
                typer.echo(str(e), err=True)
                raise typer.Exit(code=1) from e
            typer.echo(json.dumps({"removed": name}))
            return
        typer.echo("expected: add | list | remove", err=True)
        raise typer.Exit(code=2)

    @app.command("fetch")
    def fetch_cmd(
        remote_name: Annotated[str, typer.Argument(help="Remote name.")],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Fetch from a configured swarm remote (local peer)."""
        root = (cell or Path.cwd()).resolve()
        try:
            info = fetch_remote(root, remote_name)
        except (KeyError, ValueError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps(info, indent=2))

    @app.command("pull")
    def pull_cmd(
        remote_name: Annotated[str, typer.Argument(help="Remote name.")],
        ref: Annotated[
            str | None,
            typer.Argument(help="Branch on remote (default: current branch)."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Fetch and merge from a swarm remote."""
        root = (cell or Path.cwd()).resolve()
        try:
            info = pull_remote(root, remote_name, ref)
        except (KeyError, ValueError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps(info, indent=2))

    @app.command("hook")
    def hook_cmd(
        action: Annotated[str, typer.Argument(help="run")],
        name: Annotated[str, typer.Argument(help="Hook name, e.g. pre-thought.")],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Run a hook manually (respects HONEYHEX_HOOKS and config)."""
        if action != "run":
            typer.echo("only `hex hook run <name>` is supported", err=True)
            raise typer.Exit(code=2)
        root = (cell or Path.cwd()).resolve()
        res = run_named_hook(HookContext(root, name))
        echo_hook_output(res, err_stream=True)
        if res.returncode != 0:
            raise typer.Exit(code=res.returncode)

    @app.command("cell")
    def cell_cmd(
        action: Annotated[str, typer.Argument(help="init")],
        hook_stubs: Annotated[
            bool,
            typer.Option("--hook-stubs", help="Install sample hook scripts."),
        ] = False,
        guided: Annotated[
            bool,
            typer.Option(
                "--guided",
                help="Record a starter thought-commit and print next-step hints.",
            ),
        ] = False,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Initialize a HoneyHex cell under the given directory."""
        if action != "init":
            typer.echo("only `hex cell init` is supported", err=True)
            raise typer.Exit(code=2)
        root = (cell or Path.cwd()).resolve()
        created = init_cell(root, hook_stubs=hook_stubs, guided=guided)
        typer.echo(json.dumps(created, indent=2))

    @app.command("merge")
    def merge_cmd(
        branch: Annotated[str, typer.Argument(help="Branch to merge into current.")],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Merge another branch inside `.honeyhex` (Git merge)."""
        root = (cell or Path.cwd()).resolve()
        try:
            head = merge_branch(root, branch)
        except GitCommandError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        post = run_named_hook(HookContext(root, "post-merge"))
        echo_hook_output(post, err_stream=True)
        typer.echo(json.dumps({"head": head, "post_merge_hook": post.returncode}))

    @app.command("blame")
    def blame_cmd(
        rev: Annotated[
            str | None,
            typer.Option("--rev", help="Revision to blame (default: HEAD)."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
        as_json: Annotated[
            bool,
            typer.Option("--json", help="Blame lines as JSON (porcelain)."),
        ] = False,
    ) -> None:
        """Git blame on thoughts/snapshot.json."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        if as_json:
            typer.echo(git_blame_as_json(root, rev))
        else:
            typer.echo(git_blame_snapshot(root, rev), nl=False)

    @app.command("reflog")
    def reflog_cmd(
        n: Annotated[
            int | None,
            typer.Option("--max-count", "-n", help="Limit entries."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Show `.honeyhex` reflog."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        typer.echo(git_reflog(root, n), nl=False)

    @app.command("tag")
    def tag_cmd(
        name: Annotated[str, typer.Argument(help="Tag name.")],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Create a lightweight tag at HEAD in `.honeyhex`."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        create_lightweight_tag(root, name)
        typer.echo(json.dumps({"tag": name}))

    bundle_app = typer.Typer(help="ZIP export/import of thought snapshots.")

    @bundle_app.command("create")
    def bundle_create_cmd(
        out: Annotated[Path, typer.Argument(help="Output .zip path.")],
        n: Annotated[
            int | None,
            typer.Option("--max-count", "-n", help="Limit commits exported."),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Write manifest + thoughts JSON into a zip."""
        root = (cell or Path.cwd()).resolve()
        info = create_bundle(root, out, max_count=n)
        typer.echo(json.dumps(info, indent=2))

    @bundle_app.command("replay")
    def bundle_replay_cmd(
        zip_path: Annotated[
            Path,
            typer.Argument(help="Bundle zip from hex bundle create."),
        ],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Replay bundled thoughts as new commits."""
        root = (cell or Path.cwd()).resolve()
        info = replay_bundle(root, zip_path)
        typer.echo(json.dumps(info, indent=2))

    app.add_typer(bundle_app, name="bundle")

    @app.command("sign")
    def sign_cmd(
        rev: str | None = typer.Argument(
            default=None,
            help="Commit to sign (default: HEAD).",
        ),
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """HMAC-SHA256 signature sidecar (needs HONEYHEX_SIGNING_KEY)."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        repo = HoneyHexLedger(root).repo()
        sha = repo.commit(rev or "HEAD").hexsha
        try:
            path = sign_commit(root, sha)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"commit": sha, "signature": str(path)}))

    @app.command("verify")
    def verify_cmd(
        rev: str | None = typer.Argument(
            default=None,
            help="Commit to verify (default: HEAD).",
        ),
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Verify HMAC sidecar for a commit."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        repo = HoneyHexLedger(root).repo()
        sha = repo.commit(rev or "HEAD").hexsha
        try:
            ok = verify_commit(root, sha)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"commit": sha, "verified": ok}))
        if not ok:
            raise typer.Exit(code=1)

    @app.command(
        "git",
        context_settings={"allow_extra_args": True},
    )
    def git_pass_cmd(
        ctx: typer.Context,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Run arbitrary `git` with `-C .honeyhex` (escape hatch)."""
        root = (cell or Path.cwd()).resolve()
        hh = HoneyHexLedger(root).honeyhex_path
        cmd = ["git", "-C", str(hh), *ctx.args]
        r = subprocess.run(cmd, check=False)
        raise typer.Exit(code=r.returncode)

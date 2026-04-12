from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from honeyhex.adoption.export_ledger import export_html, export_markdown
from honeyhex.adoption.scrub import scrub_path, scrub_text
from honeyhex.adoption.search import search_ledger
from honeyhex.adoption.stats import ledger_stats
from honeyhex.adoption.timeutil import parse_iso_datetime
from honeyhex.adoption.validate import validate_cell
from honeyhex.branching.experiment import (
    experiment_merge,
    experiment_start,
    experiment_status,
    list_experiment_branches,
)
from honeyhex.cell.peer_merge import MergeFavor, merge_peer_ledger
from honeyhex.cli.doctor import run_doctor
from honeyhex.inspect.core import ensure_repo, iter_log, read_snapshot_at
from honeyhex.validators.llm_tone import llm_tone_audit
from honeyhex.validators.snapshot import audit_state_diff


def register_adoption_commands(app: typer.Typer) -> None:
    @app.command("search")
    def search_cmd(
        pattern: Annotated[
            str,
            typer.Argument(help="Substring to search (Python fallback without rg)."),
        ],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Search files under `.honeyhex/` (ripgrep when available)."""
        root = (cell or Path.cwd()).resolve()
        if not pattern:
            typer.echo("empty pattern", err=True)
            raise typer.Exit(code=2)
        code, out = search_ledger(root, pattern)
        if out:
            typer.echo(out)
        if code != 0:
            raise typer.Exit(code=code)

    @app.command("export")
    def export_cmd(
        format: Annotated[
            Literal["md", "html"],
            typer.Option("--format", help="Output format."),
        ] = "md",
        output: Annotated[
            Path | None,
            typer.Option("-o", "--output", help="Write to file instead of stdout."),
        ] = None,
        max_count: Annotated[
            int | None,
            typer.Option("-n", "--max-count", help="Limit commits (newest first)."),
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
                help=("Commits in git range tag..HEAD (see git rev-list)."),
            ),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Export thought history as Markdown or HTML."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        since_dt = parse_iso_datetime(since)
        until_dt = parse_iso_datetime(until)
        if format == "md":
            text = export_markdown(
                root,
                max_count=max_count,
                since=since_dt,
                until=until_dt,
                message_grep=grep,
                after_tag=after_tag,
            )
        else:
            text = export_html(
                root,
                max_count=max_count,
                since=since_dt,
                until=until_dt,
                message_grep=grep,
                after_tag=after_tag,
            )
        if output is not None:
            output.write_text(text, encoding="utf-8")
            typer.echo(json.dumps({"written": str(output)}, indent=2))
        else:
            typer.echo(text, nl=False)

    @app.command("doctor")
    def doctor_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Run environment and cell diagnostics (JSON)."""
        report = run_doctor(cell)
        typer.echo(json.dumps(report, indent=2))
        if not report.get("ok"):
            raise typer.Exit(code=1)

    @app.command("audit")
    def audit_cmd(
        rev: Annotated[
            str | None,
            typer.Argument(help="Revision to audit (default: HEAD)."),
        ] = None,
        scan_all: Annotated[
            bool,
            typer.Option("--all", help="Scan recent commits (see --max-commits)."),
        ] = False,
        max_commits: Annotated[
            int,
            typer.Option("--max-commits", help="With --all, max commits to scan."),
        ] = 50,
        llm_tone: Annotated[
            bool,
            typer.Option(
                "--llm-tone",
                help="Optional LiteLLM tone pass (needs honeyhex[llm] + API keys).",
            ),
        ] = False,
        model: Annotated[
            str,
            typer.Option("--model", help="LiteLLM model when --llm-tone is set."),
        ] = "gpt-4o-mini",
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """PII/secret audit on snapshots (local rules; optional LLM tone)."""
        if llm_tone and importlib.util.find_spec("litellm") is None:
            typer.echo("Install honeyhex[llm] for --llm-tone", err=True)
            raise typer.Exit(code=1)

        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        target = rev or "HEAD"
        results: list[dict[str, object]] = []
        any_error = False

        def _tone_block(snap_text: str) -> dict[str, object] | None:
            if not llm_tone:
                return None
            return llm_tone_audit(text=snap_text, model=model)

        if scan_all:
            for entry in iter_log(root, max_count=max_commits):
                _hx, snap = read_snapshot_at(root, entry.hexsha)
                if snap is None:
                    continue
                findings = [asdict(f) for f in audit_state_diff(snap)]
                text = snap.prompt + "\n" + snap.scratchpad
                tone = _tone_block(text)
                row: dict[str, object] = {"rev": entry.hexsha, "findings": findings}
                if tone is not None:
                    row["llm_tone"] = tone
                results.append(row)
                any_error = any_error or any(
                    f["severity"] == "error" for f in findings
                )
            typer.echo(json.dumps({"audits": results}, indent=2))
            if any_error:
                raise typer.Exit(code=1)
            return

        _hx, snap = read_snapshot_at(root, target)
        if snap is None:
            typer.echo(
                json.dumps({"rev": target, "error": "no snapshot"}),
                err=True,
            )
            raise typer.Exit(code=1)
        analyzed = audit_state_diff(snap)
        findings = [asdict(f) for f in analyzed]
        any_error = any(f.severity == "error" for f in analyzed)
        text = snap.prompt + "\n" + snap.scratchpad
        tone = _tone_block(text)
        out: dict[str, object] = {"rev": target, "findings": findings}
        if tone is not None:
            out["llm_tone"] = tone
        typer.echo(json.dumps(out, indent=2))
        if any_error:
            raise typer.Exit(code=1)

    @app.command("peer-merge")
    def peer_merge_cmd(
        remote_name: Annotated[
            str,
            typer.Argument(help="Remote name from .honeyhex/swarm.json."),
        ],
        branch: Annotated[
            str | None,
            typer.Option(
                "--branch",
                help="Remote branch to merge (default: current branch name).",
            ),
        ] = None,
        favor: Annotated[
            str,
            typer.Option(
                "--favor",
                help="Conflict bias: none | ours | theirs (same as git merge -X).",
            ),
        ] = "none",
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Fetch a swarm remote and merge it into the current ledger branch."""
        root = (cell or Path.cwd()).resolve()
        if favor not in {"none", "ours", "theirs"}:
            typer.echo("--favor must be none, ours, or theirs", err=True)
            raise typer.Exit(code=2)
        try:
            ensure_repo(root)
            head = merge_peer_ledger(
                root,
                remote_name,
                branch=branch,
                favor=cast(MergeFavor, favor),
            )
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"head": head, "remote": remote_name}, indent=2))

    @app.command("stats")
    def stats_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Local-only commit and snapshot statistics (no network)."""
        root = (cell or Path.cwd()).resolve()
        ensure_repo(root)
        typer.echo(json.dumps(ledger_stats(root), indent=2))

    @app.command("validate")
    def validate_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Check `.honeyhex` layout and config (for CI)."""
        root = (cell or Path.cwd()).resolve()
        ok, errs = validate_cell(root)
        payload = {"ok": ok, "errors": errs}
        typer.echo(json.dumps(payload, indent=2))
        if not ok:
            raise typer.Exit(code=1)

    @app.command("scrub")
    def scrub_cmd(
        path: Annotated[
            Path | None,
            typer.Argument(help="File to scrub (or use --stdin)."),
        ] = None,
        stdin: Annotated[
            bool,
            typer.Option("--stdin", help="Read from stdin."),
        ] = False,
        in_place: Annotated[
            bool,
            typer.Option(
                "--in-place",
                "-i",
                help="Overwrite file; original saved as .bak next to path.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                help="Print scrubbed text only; never write (not with -i).",
            ),
        ] = False,
    ) -> None:
        """Redact common secret patterns from text (stdout unless --in-place)."""
        if dry_run and in_place:
            typer.echo("cannot use --dry-run with --in-place", err=True)
            raise typer.Exit(code=2)
        if stdin:
            raw = sys.stdin.read()
            typer.echo(scrub_text(raw), nl=False)
            return
        if path is None:
            typer.echo("provide PATH or --stdin", err=True)
            raise typer.Exit(code=2)
        text = scrub_path(path)
        if dry_run:
            typer.echo(text, nl=False)
            return
        if in_place:
            bak = path.with_suffix(path.suffix + ".bak")
            bak.write_bytes(path.read_bytes())
            path.write_text(text, encoding="utf-8")
            typer.echo(
                json.dumps({"scrubbed": str(path), "backup": str(bak)}, indent=2),
            )
        else:
            typer.echo(text, nl=False)

    exp = typer.Typer(help="Experiment branches under honeyhex/exp/<slug>.")

    @exp.command("start")
    def exp_start_cmd(
        slug: Annotated[
            str,
            typer.Argument(help="Short name (letters, digits, hyphens)."),
        ],
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Create or switch to an experiment branch."""
        root = (cell or Path.cwd()).resolve()
        try:
            ensure_repo(root)
            name = experiment_start(root, slug)
        except Exception as e:  # noqa: BLE001
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"branch": name}, indent=2))

    @exp.command("list")
    def exp_list_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """List experiment branches."""
        root = (cell or Path.cwd()).resolve()
        try:
            ensure_repo(root)
            names = list_experiment_branches(root)
        except Exception as e:  # noqa: BLE001
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"branches": names}, indent=2))

    @exp.command("status")
    def exp_status_cmd(
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Show current branch and whether it is an experiment branch."""
        root = (cell or Path.cwd()).resolve()
        try:
            ensure_repo(root)
            st = experiment_status(root)
        except Exception as e:  # noqa: BLE001
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps(st, indent=2))

    @exp.command("merge")
    def exp_merge_cmd(
        into: Annotated[
            str | None,
            typer.Option(
                "--into",
                help="Branch to merge into (default: cell config default_branch).",
            ),
        ] = None,
        cell: Annotated[
            Path | None,
            typer.Option("--cell", help="Agent cell root (default: cwd)."),
        ] = None,
    ) -> None:
        """Merge the current experiment branch into mainline (checks out target)."""
        root = (cell or Path.cwd()).resolve()
        try:
            ensure_repo(root)
            head = experiment_merge(root, into=into)
        except (ValueError, OSError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from e
        typer.echo(json.dumps({"head": head}, indent=2))

    app.add_typer(exp, name="experiment")

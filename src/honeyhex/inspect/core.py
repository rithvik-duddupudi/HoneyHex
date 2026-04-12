from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
from pydantic import ValidationError

from honeyhex.commit.models import StateDiff, ThoughtCommit, payload_relative_path
from honeyhex.ledger.git_store import HoneyHexLedger


@dataclass(frozen=True)
class LogEntry:
    hexsha: str
    short: str
    message: str


def _repo(cell: Path) -> Repo:
    ledger = HoneyHexLedger(cell)
    return ledger.repo()


def _commit_message(commit: Any) -> str:
    m = commit.message
    if isinstance(m, bytes):
        return m.decode("utf-8", errors="replace").strip()
    return str(m).strip()


def iter_log(
    cell: Path,
    *,
    max_count: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    message_grep: str | None = None,
    after_tag: str | None = None,
) -> list[LogEntry]:
    """Return thought-commits newest first, with optional filters."""
    repo = _repo(cell)
    try:
        if after_tag:
            spec = f"{after_tag}..HEAD"
            commits = list(repo.iter_commits(spec, max_count=max_count))
        else:
            commits = list(repo.iter_commits(max_count=max_count))
    except GitCommandError as e:
        msg = f"log failed: {e}"
        raise ValueError(msg) from e
    entries: list[LogEntry] = []
    for c in commits:
        msg = _commit_message(c)
        dt = datetime.fromtimestamp(c.committed_date, tz=UTC)
        if since is not None and dt < since:
            continue
        if until is not None and dt > until:
            continue
        if message_grep is not None and message_grep not in msg:
            continue
        entries.append(
            LogEntry(
                hexsha=c.hexsha,
                short=c.hexsha[:7],
                message=msg,
            ),
        )
    return entries


def format_log_text(entries: list[LogEntry], *, oneline: bool) -> str:
    lines: list[str] = []
    for e in entries:
        if oneline:
            lines.append(f"{e.short} {e.message.splitlines()[0] if e.message else ''}")
        else:
            lines.append(f"commit {e.hexsha}")
            lines.append(f"    {e.message.replace(chr(10), chr(10) + '    ')}")
            lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def read_snapshot_at(cell: Path, rev: str) -> tuple[str, StateDiff | None]:
    """Return (revision, parsed snapshot) or None if blob missing."""
    repo = _repo(cell)
    rel = payload_relative_path()
    try:
        blob = repo.git.show(f"{rev}:{rel}")
    except GitCommandError:
        return rev, None
    data = json.loads(blob)
    try:
        return rev, StateDiff.model_validate(data)
    except ValidationError:
        pass
    if isinstance(data, dict) and isinstance(data.get("diff"), dict):
        try:
            return rev, StateDiff.model_validate(data["diff"])
        except ValidationError:
            return rev, None
    try:
        tc = ThoughtCommit.model_validate(data)
        return rev, tc.diff
    except ValidationError:
        return rev, None


def show_revision(cell: Path, rev: str, *, as_json: bool) -> str:
    """Human or JSON summary of one revision."""
    resolved = _repo(cell).commit(rev).hexsha
    _, snap = read_snapshot_at(cell, resolved)
    repo = _repo(cell)
    commit = repo.commit(resolved)
    if as_json:
        payload: dict[str, Any] = {
            "commit": resolved,
            "parent": commit.parents[0].hexsha if commit.parents else None,
            "message": _commit_message(commit),
            "snapshot": snap.model_dump() if snap else None,
        }
        return json.dumps(payload, indent=2)
    lines = [f"commit {resolved}"]
    if commit.parents:
        lines.append(f"parent {commit.parents[0].hexsha}")
    lines.append("")
    lines.append(_commit_message(commit))
    lines.append("")
    if snap is not None:
        lines.append("thoughts/snapshot.json:")
        lines.append(json.dumps(snap.model_dump(), indent=2))
    else:
        lines.append("(no snapshot.json at this revision)")
    return "\n".join(lines)


def diff_snapshots(
    cell: Path,
    rev_a: str | None,
    rev_b: str | None,
) -> str:
    """
    Diff `thoughts/snapshot.json` between two revisions.
    Defaults: rev_a=HEAD~1, rev_b=HEAD when both omitted.
    """
    repo = _repo(cell)
    rel = payload_relative_path()
    if rev_a is None and rev_b is None:
        ra, rb = "HEAD~1", "HEAD"
    elif rev_a is not None and rev_b is None:
        rb = "HEAD"
        ra = rev_a
    elif rev_a is not None and rev_b is not None:
        ra, rb = rev_a, rev_b
    else:
        msg = "provide zero, one (compare to HEAD), or two revisions"
        raise ValueError(msg)
    try:
        return str(repo.git.diff(f"{ra}:{rel}", f"{rb}:{rel}"))
    except GitCommandError as e:
        try:
            return str(repo.git.diff(ra, rb, "--", rel))
        except GitCommandError:
            msg = f"diff failed: {e}"
            raise ValueError(msg) from e


def git_log_graph(cell: Path, max_count: int | None) -> str:
    """Raw `git log --graph` output from `.honeyhex`."""
    repo = _repo(cell)
    args: list[str] = ["--graph", "--decorate", "--oneline", "--all"]
    if max_count is not None:
        args.append(f"-n{max_count}")
    return str(repo.git.log(*args))


def git_blame_snapshot(cell: Path, rev: str | None) -> str:
    repo = _repo(cell)
    rel = payload_relative_path()
    r = rev or "HEAD"
    return str(repo.git.blame("-w", r, "--", rel))


def git_reflog(cell: Path, max_count: int | None) -> str:
    repo = _repo(cell)
    if max_count is not None:
        return str(repo.git.reflog("-n", str(max_count)))
    return str(repo.git.reflog())


def ensure_repo(cell: Path) -> Repo:
    """Raise clear error if `.honeyhex` is not a Git repo."""
    try:
        return _repo(cell)
    except InvalidGitRepositoryError as e:
        msg = "not a HoneyHex cell: missing .honeyhex Git repository"
        raise ValueError(msg) from e


def log_as_json(
    cell: Path,
    max_count: int | None = None,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    message_grep: str | None = None,
    after_tag: str | None = None,
) -> str:
    entries = iter_log(
        cell,
        max_count=max_count,
        since=since,
        until=until,
        message_grep=message_grep,
        after_tag=after_tag,
    )
    payload = [
        {"hexsha": e.hexsha, "short": e.short, "message": e.message} for e in entries
    ]
    return json.dumps(payload, indent=2)


def diff_as_json(
    cell: Path,
    rev_a: str | None,
    rev_b: str | None,
) -> str:
    text = diff_snapshots(cell, rev_a, rev_b)
    return json.dumps(
        {
            "path": payload_relative_path(),
            "format": "git-unified",
            "text": text,
        },
        indent=2,
    )


def git_blame_as_json(cell: Path, rev: str | None) -> str:
    """Structured blame: line groups with commit id (git blame --porcelain)."""
    repo = _repo(cell)
    rel = payload_relative_path()
    r = rev or "HEAD"
    raw = str(repo.git.blame("--porcelain", "-w", r, "--", rel))
    rows: list[dict[str, Any]] = []
    cur: dict[str, Any] = {}
    for line in raw.splitlines():
        if line.startswith("\t"):
            rows.append({**cur, "line": line[1:]})
            cur = {}
            continue
        if len(line) >= 41 and line[40:41] == " ":
            parts = line.split(" ", 2)
            cur = {"commit": parts[0]}
            if len(parts) >= 2 and parts[1].isdigit():
                cur["orig_line"] = int(parts[1])
            if len(parts) >= 3 and parts[2].split():
                tail = parts[2].split()
                if tail and tail[-1].isdigit():
                    cur["final_line"] = int(tail[-1])
        elif line.startswith("filename "):
            cur["filename"] = line[9:]
    return json.dumps({"path": rel, "lines": rows}, indent=2)

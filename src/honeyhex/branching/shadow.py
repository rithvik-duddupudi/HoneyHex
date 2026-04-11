from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ShadowResult:
    """Outcome of a shadow-branch dual run."""

    winner: Literal["left", "right"]
    returncode: int
    stdout: str
    stderr: str


async def _wait_proc(
    proc: asyncio.subprocess.Process,
    label: Literal["left", "right"],
) -> tuple[Literal["left", "right"], int, str, str]:
    out_b, err_b = await proc.communicate()
    code = 0 if proc.returncode is None else int(proc.returncode)
    out = out_b.decode(errors="replace")
    err = err_b.decode(errors="replace")
    return label, code, out, err


def _terminate_process_group(proc: asyncio.subprocess.Process) -> None:
    if proc.pid is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        try:
            proc.terminate()
        except ProcessLookupError:
            return


async def run_dual_shell_commands(
    left_cmd: str,
    right_cmd: str,
    *,
    success_codes: frozenset[int] | None = None,
) -> ShadowResult:
    """
    Run two shell commands concurrently; the first to exit with a success code wins.
    The other process group is terminated (best-effort).
    """
    codes = success_codes if success_codes is not None else frozenset({0})

    left_p = await asyncio.create_subprocess_shell(
        left_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},
        start_new_session=True,
    )
    right_p = await asyncio.create_subprocess_shell(
        right_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},
        start_new_session=True,
    )

    t_left = asyncio.create_task(_wait_proc(left_p, "left"))
    t_right = asyncio.create_task(_wait_proc(right_p, "right"))
    pending: set[asyncio.Task[tuple[Literal["left", "right"], int, str, str]]] = set()
    pending.add(t_left)
    pending.add(t_right)

    while pending:
        done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for finished in done:
            pending.discard(finished)
            label, code, out, err = finished.result()
            if code in codes:
                other = right_p if label == "left" else left_p
                _terminate_process_group(other)
                for t in pending:
                    t.cancel()
                for t in pending:
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass
                return ShadowResult(
                    winner=label,
                    returncode=code,
                    stdout=out,
                    stderr=err,
                )

    msg = "shadow run finished without success"
    raise RuntimeError(msg)

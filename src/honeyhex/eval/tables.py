from __future__ import annotations

from typing import Any


def summarize_tabular_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Fast summary of list-of-dicts (e.g. tool outputs / CI samples) using Polars.
    Install: pip install 'honeyhex[llm]' (includes polars).
    """
    try:
        import polars as pl
    except ImportError as e:
        msg = "Install polars: pip install 'honeyhex[llm]'"
        raise ImportError(msg) from e

    if not rows:
        return {"n_rows": 0, "columns": []}
    df = pl.DataFrame(rows)
    means: dict[str, float] = {}
    for c in df.columns:
        try:
            m = df[c].mean()
            if m is None:
                continue
            means[str(c)] = float(m)  # type: ignore[arg-type]
        except Exception:
            continue
    return {
        "n_rows": len(df),
        "columns": list(df.columns),
        "numeric_means": means,
    }

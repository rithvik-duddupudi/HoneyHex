from __future__ import annotations

import json
from typing import Annotated, Any

import typer


def _httpx_mod() -> Any:
    try:
        import httpx
    except ImportError as e:
        msg = "Install registry extras: pip install 'honeyhex[registry]'"
        raise ImportError(msg) from e
    return httpx


def _registry_url() -> str:
    import os

    return os.environ.get("HONEYHEX_REGISTRY_URL", "http://127.0.0.1:8765").rstrip("/")


def register_llm_commands(app: typer.Typer) -> None:
    @app.command("llm-vote")
    def llm_vote_cmd(
        pr_id: str = typer.Option(
            ...,
            "--pr",
            help="Pull request id.",
        ),
        validator_id: Annotated[
            str,
            typer.Option("--validator-id", help="Swarm validator slot."),
        ] = "validator-a",
        model: Annotated[
            str,
            typer.Option("--model", help="LiteLLM model name."),
        ] = "gpt-4o-mini",
    ) -> None:
        """
        Call the LLM validator on a PR and POST a vote (Phase 7).
        Requires API keys for your provider (e.g. OPENAI_API_KEY).
        """
        try:
            httpx = _httpx_mod()
        except ImportError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1) from None
        url = f"{_registry_url()}/api/v1/prs/{pr_id}/llm-evaluate"
        r = httpx.post(
            url,
            json={"model": model, "validator_id": validator_id},
            timeout=120.0,
        )
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))

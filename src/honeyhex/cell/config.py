from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from honeyhex.ledger.git_store import HoneyHexLedger


class CellConfig(BaseModel):
    """Optional cell config: `config.json` or `config.toml` under `.honeyhex/`."""

    model_config = {"extra": "forbid"}

    default_branch: str = "main"
    hooks_mode: Literal["off", "safe", "full"] = "off"
    hooks: dict[str, str] = Field(
        default_factory=dict,
        description="Hook name -> script path relative to `.honeyhex/`",
    )


CONFIG_JSON = "config.json"
CONFIG_TOML = "config.toml"


def config_path_json(cell_root: Path) -> Path:
    return HoneyHexLedger(cell_root).honeyhex_path / CONFIG_JSON


def config_path_toml(cell_root: Path) -> Path:
    return HoneyHexLedger(cell_root).honeyhex_path / CONFIG_TOML


def _parse_toml_mapping(raw: str) -> dict[str, Any]:
    data = tomllib.loads(raw)
    out: dict[str, Any] = {}
    for k in ("default_branch", "hooks_mode"):
        if k in data:
            out[k] = data[k]
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        out["hooks"] = {str(a): str(b) for a, b in hooks.items()}
    return out


def load_cell_config(cell_root: Path) -> CellConfig:
    honeyhex = HoneyHexLedger(cell_root).honeyhex_path
    toml_p = honeyhex / CONFIG_TOML
    json_p = honeyhex / CONFIG_JSON
    if toml_p.is_file():
        raw = toml_p.read_text(encoding="utf-8")
        return CellConfig.model_validate(_parse_toml_mapping(raw))
    if json_p.is_file():
        data = json.loads(json_p.read_text(encoding="utf-8"))
        return CellConfig.model_validate(data)
    return CellConfig()


def save_cell_config(cell_root: Path, cfg: CellConfig) -> None:
    path = config_path_json(cell_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        cfg.model_dump_json(indent=2),
        encoding="utf-8",
    )

from __future__ import annotations

from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError


class HoneyHexLedger:
    """Git-backed store under `<cell>/.honeyhex/`."""

    HONEYHEX_DIR = ".honeyhex"

    def __init__(self, cell_root: Path) -> None:
        self.cell_root = cell_root.resolve()
        self.honeyhex_path = self.cell_root / self.HONEYHEX_DIR

    def repo(self) -> Repo:
        if not (self.honeyhex_path / ".git").is_dir():
            raise InvalidGitRepositoryError(self.honeyhex_path)
        return Repo(self.honeyhex_path)

    def init_if_missing(self) -> Repo:
        self.honeyhex_path.mkdir(parents=True, exist_ok=True)
        if (self.honeyhex_path / ".git").is_dir():
            return Repo(self.honeyhex_path)
        repo = Repo.init(self.honeyhex_path)
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "honeyhex")
            cw.set_value("user", "email", "honeyhex@local")
        return repo

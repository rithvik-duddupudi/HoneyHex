# src/honeytrail/db/store.py
from __future__ import annotations

import sqlite3
import uuid
from importlib import resources
from pathlib import Path

from honeytrail.models import RollbackResult, TrailNode, utc_now_iso


class TrailStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        pkg = resources.files("honeytrail")
        raw = (pkg / "db/schema.sql").read_text(encoding="utf-8")
        self._conn.executescript(raw)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def session_open(self, label: str = "") -> str:
        sid = uuid.uuid4().hex
        self._conn.execute(
            "INSERT INTO sessions (id, label, created_at) VALUES (?, ?, ?)",
            (sid, label, utc_now_iso()),
        )
        self._conn.commit()
        return sid

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def append_thought(
        self,
        session_id: str,
        monologue: str,
        summary: str = "",
        state_json: str = "{}",
    ) -> str:
        current_head = self.get_head(session_id)
        node_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO nodes
              (id, session_id, parent_id, kind, summary,
               monologue, state_json, created_at)
            VALUES (?, ?, ?, 'thought', ?, ?, ?, ?)
            """,
            (
                node_id,
                session_id,
                current_head,
                summary,
                monologue,
                state_json,
                utc_now_iso(),
            ),
        )
        self._conn.execute(
            "UPDATE sessions SET head_node_id = ? WHERE id = ?",
            (node_id, session_id),
        )
        self._conn.commit()
        return node_id

    def append_tool(
        self,
        session_id: str,
        tool_name: str,
        tool_input_json: str = "{}",
        tool_output_summary: str = "",
        summary: str = "",
    ) -> str:
        current_head = self.get_head(session_id)
        node_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO nodes
              (id, session_id, parent_id, kind, summary,
               monologue, state_json, tool_name, tool_input_json,
               tool_output_summary, created_at)
            VALUES (?, ?, ?, 'tool', ?, '', '{}', ?, ?, ?, ?)
            """,
            (
                node_id,
                session_id,
                current_head,
                summary,
                tool_name,
                tool_input_json,
                tool_output_summary,
                utc_now_iso(),
            ),
        )
        self._conn.execute(
            "UPDATE sessions SET head_node_id = ? WHERE id = ?",
            (node_id, session_id),
        )
        self._conn.commit()
        return node_id

    def get_head(self, session_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT head_node_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"session not found: {session_id}")
        return row["head_node_id"]  # type: ignore[return-value]

    def get_parent(self, node_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT parent_id FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"node not found: {node_id}")
        return row["parent_id"]  # type: ignore[return-value]

    def get_node(self, node_id: str) -> TrailNode:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"node not found: {node_id}")
        return TrailNode(**dict(row))

    # ------------------------------------------------------------------
    # Rollback + path
    # ------------------------------------------------------------------

    def rollback_to_parent_of_match(
        self, session_id: str, before_substring: str
    ) -> RollbackResult:
        """Walk from head backward; find node where before_substring in monologue;
        set head to that node's parent."""
        head_id = self.get_head(session_id)
        previous_head_id = head_id
        current_id = head_id
        target: str | None = None

        while current_id is not None:
            row = self._conn.execute(
                "SELECT id, parent_id, monologue FROM nodes WHERE id = ?",
                (current_id,),
            ).fetchone()
            if row is None:
                break
            if before_substring.lower() in row["monologue"].lower():
                target = row["id"]
                break
            current_id = row["parent_id"]

        if target is None:
            raise ValueError(
                f"No node matching '{before_substring}' found in session {session_id}"
            )

        new_head_row = self._conn.execute(
            "SELECT parent_id FROM nodes WHERE id = ?", (target,)
        ).fetchone()
        new_head_id = new_head_row["parent_id"]

        self._conn.execute(
            "UPDATE sessions SET head_node_id = ? WHERE id = ?",
            (new_head_id, session_id),
        )
        self._conn.commit()
        return RollbackResult(
            previous_head_id=previous_head_id, new_head_id=new_head_id
        )

    def linear_path_to_head(self, session_id: str) -> list[TrailNode]:
        """Return nodes from root to head by walking parent_id links."""
        head_id = self.get_head(session_id)
        if head_id is None:
            return []
        path: list[TrailNode] = []
        current_id: str | None = head_id
        while current_id is not None:
            node = self.get_node(current_id)
            path.append(node)
            current_id = node.parent_id
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Fork / branch / merge
    # ------------------------------------------------------------------

    def fork(self, session_id: str, branch_name: str, from_node_id: str) -> str:
        """Create a fork node at from_node_id and register named branch."""
        node_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO nodes
              (id, session_id, parent_id, kind, summary,
               monologue, state_json, branch_label, created_at)
            VALUES (?, ?, ?, 'fork', ?, '', '{}', ?, ?)
            """,
            (
                node_id,
                session_id,
                from_node_id,
                f"fork:{branch_name}",
                branch_name,
                utc_now_iso(),
            ),
        )
        self._conn.execute(
            """
            INSERT INTO branches (session_id, name, tip_node_id)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, name)
            DO UPDATE SET tip_node_id = excluded.tip_node_id
            """,
            (session_id, branch_name, node_id),
        )
        # Register "main" branch if not yet present
        self._conn.execute(
            """
            INSERT OR IGNORE INTO branches (session_id, name, tip_node_id)
            VALUES (?, 'main', ?)
            """,
            (session_id, from_node_id),
        )
        self._conn.commit()
        return node_id

    def checkout_branch(self, session_id: str, branch_name: str) -> None:
        """Move session head to the named branch tip."""
        row = self._conn.execute(
            "SELECT tip_node_id FROM branches WHERE session_id = ? AND name = ?",
            (session_id, branch_name),
        ).fetchone()
        if row is None:
            raise KeyError(f"branch not found: {branch_name}")
        self._conn.execute(
            "UPDATE sessions SET head_node_id = ? WHERE id = ?",
            (row["tip_node_id"], session_id),
        )
        self._conn.commit()

    def merge_into_current(
        self, session_id: str, other_branch: str, summary: str = ""
    ) -> str:
        """Create merge node: parent_A = current head, parent_B = other branch tip."""
        head_id = self.get_head(session_id)
        other_row = self._conn.execute(
            "SELECT tip_node_id FROM branches WHERE session_id = ? AND name = ?",
            (session_id, other_branch),
        ).fetchone()
        if other_row is None:
            raise KeyError(f"branch not found: {other_branch}")
        merge_parent_b = other_row["tip_node_id"]

        node_id = uuid.uuid4().hex
        self._conn.execute(
            """
            INSERT INTO nodes
              (id, session_id, parent_id, kind, summary,
               monologue, state_json, merge_parent_b_id, created_at)
            VALUES (?, ?, ?, 'merge', ?, '', '{}', ?, ?)
            """,
            (node_id, session_id, head_id, summary, merge_parent_b, utc_now_iso()),
        )
        self._conn.execute(
            "UPDATE sessions SET head_node_id = ? WHERE id = ?",
            (node_id, session_id),
        )
        self._conn.commit()
        return node_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

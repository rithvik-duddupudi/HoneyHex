-- Honey-Trail: append-only reasoning graph + session head pointers
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL DEFAULT '',
  honeyhex_cell TEXT,
  created_at TEXT NOT NULL,
  head_node_id TEXT,
  FOREIGN KEY (head_node_id) REFERENCES nodes(id)
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  parent_id TEXT REFERENCES nodes(id),
  kind TEXT NOT NULL CHECK (kind IN ('thought', 'tool', 'fork', 'merge', 'compact')),
  summary TEXT NOT NULL DEFAULT '',
  monologue TEXT NOT NULL DEFAULT '',
  state_json TEXT NOT NULL DEFAULT '{}',
  tool_name TEXT,
  tool_input_json TEXT,
  tool_output_summary TEXT,
  branch_label TEXT,
  merge_parent_b_id TEXT REFERENCES nodes(id),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_session ON nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at);

CREATE TABLE IF NOT EXISTS branches (
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  tip_node_id TEXT NOT NULL REFERENCES nodes(id),
  PRIMARY KEY (session_id, name)
);

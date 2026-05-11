CREATE TABLE IF NOT EXISTS library_entries (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    domain TEXT,
    title TEXT,
    workflow_id TEXT,
    workflow_node TEXT,
    tool TEXT,
    vendor TEXT,
    stage TEXT,
    short_description TEXT,
    detail_path TEXT,
    tags TEXT,
    source_index TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_library_kind ON library_entries(kind);
CREATE INDEX IF NOT EXISTS idx_library_domain ON library_entries(domain);
CREATE INDEX IF NOT EXISTS idx_library_tool ON library_entries(tool);
CREATE INDEX IF NOT EXISTS idx_library_workflow ON library_entries(workflow_id);
CREATE INDEX IF NOT EXISTS idx_library_node ON library_entries(workflow_node);
CREATE INDEX IF NOT EXISTS idx_library_stage ON library_entries(stage);

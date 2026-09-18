-- Outbound drafts queue: steve posts quote drafts here; they send once
-- Workers Paid + SENDER binding are enabled. Until then this is the honest queue.
CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY,
  to_address TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);

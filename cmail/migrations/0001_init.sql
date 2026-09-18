-- cmail global D1 index. Mailbox DO = canonical state; D1 = searchable view.
CREATE TABLE IF NOT EXISTS domains (
  domain TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS mailboxes (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL REFERENCES domains(domain),
  local_part TEXT NOT NULL,
  address TEXT NOT NULL UNIQUE,
  agent TEXT,
  permissions TEXT NOT NULL DEFAULT '["READ","DRAFT"]',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS aliases (
  alias TEXT PRIMARY KEY,
  target_mailbox TEXT NOT NULL REFERENCES mailboxes(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS messages (
  message_id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  domain TEXT NOT NULL,
  mailbox TEXT NOT NULL,
  sender TEXT NOT NULL,
  recipients TEXT NOT NULL DEFAULT '[]',
  subject TEXT NOT NULL DEFAULT '',
  received_at TEXT NOT NULL DEFAULT (datetime('now')),
  classification TEXT NOT NULL DEFAULT 'fyi',
  importance INTEGER NOT NULL DEFAULT 0,
  needs_reply INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new',
  summary TEXT NOT NULL DEFAULT '',
  entities_json TEXT NOT NULL DEFAULT '{}',
  labels_json TEXT NOT NULL DEFAULT '[]',
  mailbox_do_id TEXT NOT NULL,
  r2_raw_key TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_needs_reply ON messages(needs_reply, importance DESC);
CREATE INDEX IF NOT EXISTS idx_messages_mailbox ON messages(mailbox, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_domain ON messages(domain, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '',
  detail TEXT NOT NULL DEFAULT ''
);
-- borrowed from AgentMail.mx: groups + scoped API tokens + webhook dispatch
CREATE TABLE IF NOT EXISTS groups (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL REFERENCES domains(domain),
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS group_members (
  group_id TEXT NOT NULL REFERENCES groups(id),
  mailbox TEXT NOT NULL REFERENCES mailboxes(id),
  PRIMARY KEY (group_id, mailbox)
);
CREATE TABLE IF NOT EXISTS api_tokens (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  scopes TEXT NOT NULL DEFAULT '["READ"]',
  domains TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS webhooks (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  events TEXT NOT NULL DEFAULT '["email.received"]',
  secret TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- UTF-8 throughout; Hebrew stored as NFC text in SQLite.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS participant (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  display_name TEXT NOT NULL,
  email TEXT,
  role TEXT NOT NULL CHECK (role IN ('support', 'oncall', 'admin')),
  gender TEXT NOT NULL CHECK (gender IN ('M', 'F')),
  region TEXT NOT NULL CHECK (region IN ('IL', 'NA')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shift (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  operational_date TEXT NOT NULL,
  region TEXT NOT NULL CHECK (region IN ('IL', 'NA')),
  slot_label TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  assigned_participant_id INTEGER REFERENCES participant(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (operational_date, slot_label)
);

CREATE INDEX IF NOT EXISTS idx_shift_operational_date ON shift(operational_date);
CREATE INDEX IF NOT EXISTS idx_shift_region ON shift(region);
CREATE INDEX IF NOT EXISTS idx_shift_assigned ON shift(assigned_participant_id);
CREATE INDEX IF NOT EXISTS idx_shift_starts ON shift(starts_at);

CREATE TABLE IF NOT EXISTS coverage_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL REFERENCES shift(id),
  originator_participant_id INTEGER NOT NULL REFERENCES participant(id),
  status TEXT NOT NULL CHECK (status IN ('open', 'approved', 'cancelled')),
  approved_offer_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  decided_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_request_shift ON coverage_request(shift_id);
CREATE INDEX IF NOT EXISTS idx_request_originator ON coverage_request(originator_participant_id);

CREATE TABLE IF NOT EXISTS offer (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES coverage_request(id),
  responder_participant_id INTEGER NOT NULL REFERENCES participant(id),
  offer_kind TEXT NOT NULL CHECK (offer_kind IN ('coverage', 'swap')),
  swap_shift_id INTEGER REFERENCES shift(id),
  status TEXT NOT NULL CHECK (status IN ('pending', 'withdrawn')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  withdrawn_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_offer_request ON offer(request_id);

-- Approved offer must belong to the same request (enforced in application layer for MVP).

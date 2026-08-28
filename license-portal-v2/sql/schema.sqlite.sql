CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hospital_name TEXT NOT NULL,
  facility_code TEXT NULL,
  amount_pesewas INTEGER NOT NULL,
  duration_months INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'GHS',
  notes TEXT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  billing_deadline TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  customer_id INTEGER NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL,
  license_id TEXT NOT NULL UNIQUE,
  customer_label TEXT NOT NULL,
  facility_code TEXT NULL,
  valid_from TEXT NOT NULL,
  valid_until TEXT NOT NULL,
  notes TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL,
  license_id TEXT NULL,
  paystack_reference TEXT NOT NULL UNIQUE,
  paystack_access_code TEXT NULL,
  amount_pesewas INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'GHS',
  duration_months INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  channel TEXT NOT NULL DEFAULT 'paystack',
  paid_at TEXT NULL,
  period_from TEXT NULL,
  period_until TEXT NULL,
  paystack_prior_refs TEXT NULL,
  raw_payload TEXT NULL,
  notes TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  doc_type TEXT NOT NULL,
  doc_number TEXT NOT NULL UNIQUE,
  file_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE TABLE IF NOT EXISTS sequences (
  name TEXT PRIMARY KEY,
  next_value INTEGER NOT NULL
);

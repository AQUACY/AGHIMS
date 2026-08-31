-- MySQL schema for Hostinger / phpMyAdmin (same as schema.mysql.sql).
-- The app also applies this on boot when DATABASE_MODE=mysql.

CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  hospital_name VARCHAR(255) NOT NULL,
  facility_code VARCHAR(64) NULL,
  amount_pesewas INT NOT NULL,
  duration_months INT NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'GHS',
  notes TEXT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  billing_deadline DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL,
  customer_id INT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_customer (customer_id),
  CONSTRAINT fk_users_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS licenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  license_id VARCHAR(48) NOT NULL,
  customer_label VARCHAR(255) NOT NULL,
  facility_code VARCHAR(64) NULL,
  valid_from DATETIME NOT NULL,
  valid_until DATETIME NOT NULL,
  notes TEXT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_licenses_license_id (license_id),
  KEY idx_licenses_customer (customer_id),
  CONSTRAINT fk_licenses_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  license_id VARCHAR(48) NULL,
  paystack_reference VARCHAR(128) NOT NULL,
  paystack_access_code VARCHAR(128) NULL,
  amount_pesewas INT NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'GHS',
  duration_months INT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  channel VARCHAR(32) NOT NULL DEFAULT 'paystack',
  paid_at DATETIME NULL,
  period_from DATETIME NULL,
  period_until DATETIME NULL,
  paystack_prior_refs TEXT NULL,
  raw_payload TEXT NULL,
  notes TEXT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_payments_reference (paystack_reference),
  KEY idx_payments_customer (customer_id),
  KEY idx_payments_status (status),
  CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  payment_id INT NOT NULL,
  customer_id INT NOT NULL,
  doc_type VARCHAR(16) NOT NULL,
  doc_number VARCHAR(64) NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_documents_number (doc_number),
  KEY idx_documents_payment (payment_id),
  KEY idx_documents_customer (customer_id),
  CONSTRAINT fk_documents_payment FOREIGN KEY (payment_id) REFERENCES payments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sequences (
  name VARCHAR(32) PRIMARY KEY,
  next_value INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reminder_sends (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  kind VARCHAR(16) NOT NULL,
  cycle_key VARCHAR(64) NOT NULL,
  to_email VARCHAR(255) NOT NULL,
  subject VARCHAR(255) NULL,
  status VARCHAR(16) NOT NULL,
  error TEXT NULL,
  created_at DATETIME NOT NULL,
  KEY idx_reminders_customer (customer_id),
  KEY idx_reminders_lookup (customer_id, kind, cycle_key),
  CONSTRAINT fk_reminders_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

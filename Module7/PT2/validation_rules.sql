-- validation_rules.sql
-- Schema for storing validation rules

CREATE TABLE IF NOT EXISTS validation_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_name TEXT NOT NULL UNIQUE,
  regex_pattern TEXT,
  error_message TEXT NOT NULL
);

-- Seed data
INSERT OR IGNORE INTO validation_rules (rule_name, regex_pattern, error_message) VALUES
('email_format', '^[^\s@]+@[^\s@]+\.[^\s@]+$', 'Invalid email format. Expected e.g. user@example.com'),
('password_min_length', NULL, 'Password must be at least 8 characters long'),
('password_has_number', '\\d', 'Password must contain at least one number'),
('password_has_special', '[!@#$%^&*(),.?":{}|<>\\[\\]\\/\\\\_\-+=~`;:]', 'Password must contain at least one special character'),
('phone_international', '^\\+?[1-9]\\d{6,14}$', 'Phone number must be in international format, e.g. +14155552671');

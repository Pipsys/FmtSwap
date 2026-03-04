-- ============================================================
--  PDF→DOCX Converter — PostgreSQL initialization script
--  Run once before starting the backend:
--    psql -U postgres -f init_db.sql
-- ============================================================

-- 1. Create dedicated database user (change password!)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pdf_user') THEN
    CREATE USER pdf_user WITH PASSWORD 'pdf_password';
  END IF;
END
$$;

-- 2. Create database
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'pdf2docx') THEN
    PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE pdf2docx OWNER pdf_user');
  END IF;
END
$$;

-- Connect to the target database before creating objects
\connect pdf2docx

-- Allow the app user to work in the public schema
GRANT USAGE  ON SCHEMA public TO pdf_user;
GRANT CREATE ON SCHEMA public TO pdf_user;

-- ============================================================
--  ENUM type for task status
-- ============================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskstatus') THEN
    CREATE TYPE taskstatus AS ENUM ('pending', 'processing', 'done', 'failed');
  END IF;
END
$$;

-- ============================================================
--  TABLE: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL          PRIMARY KEY,
    email            VARCHAR(255)    NOT NULL UNIQUE,
    username         VARCHAR(64)     NOT NULL UNIQUE,
    hashed_password  TEXT            NOT NULL,
    twofa_enabled    BOOLEAN         NOT NULL DEFAULT FALSE,
    twofa_secret     VARCHAR(128),
    twofa_pending_secret VARCHAR(128),
    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- ============================================================
--  TABLE: conversion_tasks
-- ============================================================
CREATE TABLE IF NOT EXISTS conversion_tasks (
    id                SERIAL          PRIMARY KEY,
    task_uuid         UUID            NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    user_id           INTEGER         REFERENCES users (id) ON DELETE SET NULL,
    conversion_type   VARCHAR(32)     NOT NULL DEFAULT 'pdf_to_docx',
    original_filename TEXT            NOT NULL,
    output_filename   TEXT,                          -- NULL until conversion completes
    status            taskstatus      NOT NULL DEFAULT 'pending',
    error_message     TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id   ON conversion_tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_task_uuid ON conversion_tasks (task_uuid);
CREATE INDEX IF NOT EXISTS idx_tasks_status    ON conversion_tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_conversion_type ON conversion_tasks (conversion_type);

-- ============================================================
--  TABLE: hosted_files
-- ============================================================
CREATE TABLE IF NOT EXISTS hosted_files (
    id                SERIAL          PRIMARY KEY,
    user_id           INTEGER         REFERENCES users (id) ON DELETE CASCADE,
    guest_session_id  VARCHAR(64),
    guest_ip          VARCHAR(64),
    public_token      VARCHAR(64)     NOT NULL UNIQUE,
    original_filename VARCHAR(512)    NOT NULL,
    stored_filename   VARCHAR(512)    NOT NULL UNIQUE,
    content_type      VARCHAR(255),
    size_bytes        BIGINT          NOT NULL,
    description       TEXT,
    password_hash     VARCHAR(255),
    download_count    INTEGER         NOT NULL DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_hosted_files_user_id ON hosted_files (user_id);
CREATE INDEX IF NOT EXISTS idx_hosted_files_session ON hosted_files (guest_session_id);
CREATE INDEX IF NOT EXISTS idx_hosted_files_ip ON hosted_files (guest_ip);
CREATE INDEX IF NOT EXISTS idx_hosted_files_token ON hosted_files (public_token);
CREATE INDEX IF NOT EXISTS idx_hosted_files_expiry ON hosted_files (expires_at);

-- ============================================================
--  TABLE: hosted_file_visits
-- ============================================================
CREATE TABLE IF NOT EXISTS hosted_file_visits (
    id                SERIAL          PRIMARY KEY,
    hosted_file_id    INTEGER         NOT NULL REFERENCES hosted_files (id) ON DELETE CASCADE,
    event_type        VARCHAR(16)     NOT NULL,
    ip                VARCHAR(64),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hosted_visits_file_id ON hosted_file_visits (hosted_file_id);
CREATE INDEX IF NOT EXISTS idx_hosted_visits_created_at ON hosted_file_visits (created_at);
CREATE INDEX IF NOT EXISTS idx_hosted_visits_event_type ON hosted_file_visits (event_type);

-- ============================================================
--  Auto-update updated_at via trigger
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON conversion_tasks;
CREATE TRIGGER trg_tasks_updated_at
  BEFORE UPDATE ON conversion_tasks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
--  Grant table-level permissions to app user
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users             TO pdf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE conversion_tasks  TO pdf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE hosted_files      TO pdf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE hosted_file_visits TO pdf_user;
GRANT USAGE, SELECT ON SEQUENCE users_id_seq                    TO pdf_user;
GRANT USAGE, SELECT ON SEQUENCE conversion_tasks_id_seq         TO pdf_user;
GRANT USAGE, SELECT ON SEQUENCE hosted_files_id_seq             TO pdf_user;
GRANT USAGE, SELECT ON SEQUENCE hosted_file_visits_id_seq       TO pdf_user;

-- ============================================================
--  Done
-- ============================================================
\echo '>>> Database pdf2docx initialised successfully.'

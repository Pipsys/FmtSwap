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
    user_id           INTEGER         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
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
GRANT USAGE, SELECT ON SEQUENCE users_id_seq                    TO pdf_user;
GRANT USAGE, SELECT ON SEQUENCE conversion_tasks_id_seq         TO pdf_user;

-- ============================================================
--  Done
-- ============================================================
\echo '>>> Database pdf2docx initialised successfully.'

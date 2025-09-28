-- AI Мага Database Initialization
-- This file runs when PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application user (if different from default)
-- GRANT ALL PRIVILEGES ON DATABASE ai_maga TO maga;

-- Set default privileges for future tables
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO maga;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO maga;

-- Database is ready for migrations
SELECT 'AI Мага database initialized successfully' as status;

-- PostgreSQL initialization script
-- This script runs when the container starts for the first time

-- Create additional schemas if needed
-- CREATE SCHEMA IF NOT EXISTS app_schema;

-- Create sample users (optional)
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- GRANT CONNECT ON DATABASE wccc TO app_user;
-- GRANT USAGE ON SCHEMA public TO app_user;
-- GRANT CREATE ON SCHEMA public TO app_user;

-- Example table creation (optional)
/*
CREATE TABLE IF NOT EXISTS sample_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
*/
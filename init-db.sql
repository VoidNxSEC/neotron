-- Initialize databases for Temporal and MLflow
-- PostgreSQL initialization script

-- Create databases
CREATE DATABASE IF NOT EXISTS temporal;
CREATE DATABASE IF NOT EXISTS mlflow;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE temporal TO neutron;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO neutron;

-- MLflow-specific setup
\c mlflow;

-- Create schema for MLflow (it will auto-create tables)
CREATE SCHEMA IF NOT EXISTS mlflow;
GRANT ALL ON SCHEMA mlflow TO neutron;

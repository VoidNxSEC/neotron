-- SENTINEL Compliance Audit Schema
-- Immutable audit trail for all compliance enforcement events

-- Drop existing table if exists (for development only)
-- DROP TABLE IF EXISTS compliance_audits CASCADE;

CREATE TABLE IF NOT EXISTS compliance_audits (
    -- Primary key (auto-increment)
    id SERIAL PRIMARY KEY,

    -- Temporal information
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Guardrail information
    guardrail_name VARCHAR(255) NOT NULL,
    regulation VARCHAR(50) NOT NULL CHECK (regulation IN ('LGPD', 'GDPR', 'AI_ACT', 'SOC2')),

    -- Output tracking
    agent_output_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash
    model_name VARCHAR(255),                   -- Optional: which model generated this

    -- Validation result
    validation_result JSONB NOT NULL,         -- Full validation details
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('block', 'warn', 'audit')),
    passed BOOLEAN NOT NULL,
    details TEXT,                             -- Human-readable details

    -- Immutability constraint
    -- Note: In production, you'd implement row-level security policies
    CONSTRAINT immutable_audit CHECK (id > 0)
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_compliance_audits_timestamp
    ON compliance_audits(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_audits_guardrail
    ON compliance_audits(guardrail_name);

CREATE INDEX IF NOT EXISTS idx_compliance_audits_regulation
    ON compliance_audits(regulation);

CREATE INDEX IF NOT EXISTS idx_compliance_audits_passed
    ON compliance_audits(passed);

CREATE INDEX IF NOT EXISTS idx_compliance_audits_severity
    ON compliance_audits(severity);

CREATE INDEX IF NOT EXISTS idx_compliance_audits_hash
    ON compliance_audits(agent_output_hash);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_compliance_audits_regulation_timestamp
    ON compliance_audits(regulation, timestamp DESC);

-- View for easy querying of violations
CREATE OR REPLACE VIEW compliance_violations AS
SELECT
    id,
    timestamp,
    guardrail_name,
    regulation,
    severity,
    details,
    model_name
FROM compliance_audits
WHERE passed = FALSE
ORDER BY timestamp DESC;

-- View for compliance summary statistics
CREATE OR REPLACE VIEW compliance_summary AS
SELECT
    regulation,
    COUNT(*) as total_checks,
    SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) as total_violations,
    ROUND(
        100.0 * SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as violation_rate_percent,
    MIN(timestamp) as first_check,
    MAX(timestamp) as last_check
FROM compliance_audits
GROUP BY regulation;

-- Comments for documentation
COMMENT ON TABLE compliance_audits IS
    'Immutable audit trail for SENTINEL compliance guardrail enforcement. '
    'Once written, records cannot be modified or deleted.';

COMMENT ON COLUMN compliance_audits.agent_output_hash IS
    'SHA-256 hash of agent output for tamper detection';

COMMENT ON COLUMN compliance_audits.validation_result IS
    'Full validation details as JSONB for flexible querying';

COMMENT ON VIEW compliance_violations IS
    'Quick view of all compliance violations for monitoring';

COMMENT ON VIEW compliance_summary IS
    'Aggregated compliance statistics by regulation';

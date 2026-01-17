# SENTINEL Guidelines & Best Practices

**Production Deployment Guide for Compliance Guardrails**

---

## Table of Contents

1. [Deployment Checklist](#deployment-checklist)
2. [Production Architecture](#production-architecture)
3. [Performance Optimization](#performance-optimization)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Incident Response](#incident-response)
6. [Scaling Guidelines](#scaling-guidelines)
7. [Security Best Practices](#security-best-practices)
8. [Regulatory Compliance](#regulatory-compliance)
9. [Team Responsibilities](#team-responsibilities)

---

## Deployment Checklist

### Pre-Production

- [ ] **Database Setup**
  - [ ] PostgreSQL 15+ installed and configured
  - [ ] Schema applied (`neutron/compliance/schema.sql`)
  - [ ] Indexes created on `timestamp`, `regulation`, `guardrail_name`
  - [ ] Connection pooling configured (pgBouncer recommended)
  - [ ] Backup strategy in place (daily backups, 90-day retention)

- [ ] **Environment Configuration**
  - [ ] `DATABASE_URL` environment variable set
  - [ ] Connection string uses SSL (`sslmode=require`)
  - [ ] Database credentials in secret management (Vault, AWS Secrets Manager)
  - [ ] Temporal server connection configured

- [ ] **Testing**
  - [ ] All unit tests passing (`pytest tests/compliance/`)
  - [ ] Integration tests passing (`pytest tests/compliance/test_workflow_integration.py`)
  - [ ] Demo script runs successfully (`python scripts/demo_sentinel.py`)
  - [ ] Load testing completed (see [Performance](#performance-optimization))

- [ ] **Documentation**
  - [ ] Team trained on SENTINEL usage
  - [ ] Runbooks created for common scenarios
  - [ ] On-call procedures documented
  - [ ] Compliance team briefed on audit capabilities

### Production Deployment

- [ ] **Gradual Rollout**
  - [ ] Week 1: 10% traffic (shadow mode - log only, don't block)
  - [ ] Week 2: 25% traffic (enforce blocking for Article 18)
  - [ ] Week 3: 50% traffic
  - [ ] Week 4: 100% traffic

- [ ] **Monitoring Setup**
  - [ ] Metrics dashboards configured (Grafana/Datadog)
  - [ ] Alerts configured (see [Monitoring](#monitoring--alerting))
  - [ ] Log aggregation enabled (ELK/Splunk)
  - [ ] Audit log queries tested

- [ ] **Rollback Plan**
  - [ ] Feature flag for disabling SENTINEL
  - [ ] Rollback procedure documented and tested
  - [ ] Incident response team identified

---

## Production Architecture

### High Availability

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼────┐             ┌─────▼────┐
   │ Temporal │             │ Temporal │
   │ Worker 1 │             │ Worker 2 │
   └────┬────┘             └─────┬────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   SENTINEL Activities   │
        │  (validate_agent_output) │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   PostgreSQL Cluster    │
        │  (Primary + 2 Replicas) │
        │   Audit Trail Storage   │
        └─────────────────────────┘
```

### Database Configuration

**Primary Database:**
- Handles all writes (audit logs)
- Synchronous replication to 1 standby
- Automatic failover with Patroni

**Read Replicas (2+):**
- Handle audit log queries
- Asynchronous replication from primary
- Load balanced for read traffic

**Connection Pooling:**
```python
# config.py
DATABASE_CONFIG = {
    "min_size": 10,      # Minimum pool connections
    "max_size": 100,     # Maximum pool connections
    "max_queries": 50000,  # Recycle connection after N queries
    "max_inactive_time": 300,  # Timeout inactive connections (5 min)
}
```

### Caching Strategy

**Do NOT cache:**
- ❌ Guardrail enforcement results (must be fresh)
- ❌ Audit log writes (must be immediate)

**Can cache:**
- ✅ Guardrail definitions (1 hour TTL)
- ✅ Aggregate statistics (5 min TTL)
- ✅ Audit log queries (1 min TTL, invalidate on new writes)

---

## Performance Optimization

### Benchmarks

Target SLAs:
- **Validation latency:** < 100ms (p99)
- **Audit log write:** < 50ms (p99)
- **Audit query:** < 500ms for 1000 records (p99)
- **Throughput:** 1000 validations/sec per worker

### Optimization Techniques

#### 1. Batch Audit Logging

```python
# Instead of: Log each validation individually
for output in outputs:
    enforced = guardrail.enforce(output)  # Writes to DB

# Do: Batch validation, then batch log
results = []
audit_data = []

for output in outputs:
    result = guardrail.check(output)  # No DB write
    results.append(result)
    audit_data.append({"guardrail": ..., "result": result})

# Single batch write
logger.batch_log(audit_data)
```

#### 2. Async Audit Logging

```python
# Use async logging for non-blocking enforcement
async def enforce_async(output):
    result = guardrail.check(output)

    # Non-blocking audit log
    asyncio.create_task(logger.log_async(audit_data))

    if not result.passed and severity == "block":
        raise ComplianceViolation(...)

    return EnforcedOutput(...)
```

#### 3. Database Indexing

```sql
-- Essential indexes (already in schema.sql)
CREATE INDEX idx_audits_timestamp ON compliance_audits(timestamp DESC);
CREATE INDEX idx_audits_regulation ON compliance_audits(regulation);
CREATE INDEX idx_audits_guardrail ON compliance_audits(guardrail_name);
CREATE INDEX idx_audits_passed ON compliance_audits(passed);

-- Composite indexes for common queries
CREATE INDEX idx_audits_reg_time ON compliance_audits(regulation, timestamp DESC);
CREATE INDEX idx_audits_reg_passed ON compliance_audits(regulation, passed);
```

#### 4. Partition Audit Table

For high-volume deployments (>1M audits/day):

```sql
-- Partition by month
CREATE TABLE compliance_audits (
    -- ... columns
) PARTITION BY RANGE (timestamp);

CREATE TABLE compliance_audits_2026_01 PARTITION OF compliance_audits
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE compliance_audits_2026_02 PARTITION OF compliance_audits
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Auto-create partitions with pg_partman
```

### Load Testing

```bash
# Install locust
pip install locust

# Create load test
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between
from neutron.compliance.auditors import lgpd_art18_explanation_guardrail
from neutron.compliance.sentinel import AgentOutput

class SentinelUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def validate_output(self):
        output = AgentOutput(
            content="Test output",
            has_explanation=True,
            explanation="Test explanation for load testing purposes.",
            explanation_quality=0.85
        )
        enforced = lgpd_art18_explanation_guardrail.enforce(output)
EOF

# Run load test
locust -f locustfile.py --users 100 --spawn-rate 10
```

**Expected Results:**
- 100 users: < 100ms p99 latency
- 500 users: < 200ms p99 latency
- 1000 users: < 500ms p99 latency

---

## Monitoring & Alerting

### Key Metrics

#### 1. Validation Metrics

```python
# Prometheus metrics (add to workflows.py)
from prometheus_client import Counter, Histogram

validation_total = Counter(
    'sentinel_validations_total',
    'Total validations performed',
    ['regulation', 'guardrail', 'status']
)

validation_latency = Histogram(
    'sentinel_validation_latency_seconds',
    'Validation latency',
    ['guardrail']
)

# In validate_agent_output_activity:
with validation_latency.labels(guardrail=guardrail.name).time():
    enforced = guardrail.enforce(output)

validation_total.labels(
    regulation=guardrail.regulation,
    guardrail=guardrail.name,
    status='passed' if enforced.validation_result.passed else 'failed'
).inc()
```

#### 2. Database Metrics

Monitor:
- Connection pool utilization (alert if > 80%)
- Query latency (alert if p99 > 500ms)
- Write throughput (audits/sec)
- Replication lag (alert if > 10s)

#### 3. Compliance Metrics

```sql
-- Daily compliance rate
SELECT
    DATE(timestamp) as date,
    regulation,
    COUNT(*) as total_audits,
    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed,
    ROUND(100.0 * SUM(CASE WHEN passed THEN 1 ELSE 0 END) / COUNT(*), 2) as compliance_rate
FROM compliance_audits
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp), regulation
ORDER BY date DESC, regulation;
```

### Alerts

#### Critical Alerts (PagerDuty)

1. **Compliance Rate Drop**
   - Condition: Compliance rate < 95% for any regulation
   - Action: Page on-call engineer immediately
   - Runbook: Check for guardrail misconfiguration

2. **Database Down**
   - Condition: Cannot connect to PostgreSQL
   - Action: Page DBA + on-call engineer
   - Runbook: Failover to replica

3. **High Blocking Rate**
   - Condition: > 50% of validations blocked (Article 18)
   - Action: Page ML team + compliance team
   - Runbook: Check if models stopped generating explanations

#### Warning Alerts (Slack)

1. **Elevated Latency**
   - Condition: p99 validation latency > 200ms
   - Action: Notify engineering team
   - Runbook: Check database load, add read replicas

2. **Increased Violations**
   - Condition: Violation rate increased by 50% vs. previous day
   - Action: Notify compliance team
   - Runbook: Review recent model changes

3. **Audit Log Backlog**
   - Condition: Audit write queue > 1000
   - Action: Notify engineering team
   - Runbook: Scale up workers, check database performance

### Dashboards

**Grafana Dashboard: SENTINEL Overview**

Panels:
1. Validations per second (time series)
2. Compliance rate by regulation (gauge)
3. Validation latency p50/p99 (graph)
4. Top violations by guardrail (table)
5. Database connection pool (gauge)
6. Audit log write latency (histogram)

---

## Incident Response

### Runbooks

#### Runbook 1: Compliance Rate Drop

**Symptom:** Compliance rate drops below 95%

**Diagnosis:**
1. Check which guardrail is failing: `SELECT guardrail_name, COUNT(*) FROM compliance_audits WHERE passed = false AND timestamp > NOW() - INTERVAL '1 hour' GROUP BY guardrail_name;`
2. Review recent deployments (ML models, config changes)
3. Check guardrail logs for error messages

**Resolution:**
- If model issue: Rollback model deployment
- If guardrail misconfigured: Fix configuration, redeploy
- If legitimate violations: Alert compliance team, investigate root cause

**Prevention:**
- Add pre-deployment validation tests
- Gradual model rollouts (canary testing)

#### Runbook 2: Database Performance Degradation

**Symptom:** Audit log writes taking > 500ms

**Diagnosis:**
1. Check connection pool: `SELECT count(*) FROM pg_stat_activity WHERE state = 'active';`
2. Check slow queries: `SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;`
3. Check replication lag: `SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();`

**Resolution:**
- If connection pool exhausted: Increase pool size, add workers
- If slow queries: Add indexes, optimize queries
- If replication lag: Add read replicas, increase replication bandwidth

**Prevention:**
- Capacity planning (add replicas before hitting limits)
- Regular vacuum/analyze
- Partition large tables

#### Runbook 3: SENTINEL Service Down

**Symptom:** All validations failing with timeout errors

**Diagnosis:**
1. Check Temporal worker status: `temporal workflow list --workflow_type=AdaptiveMLPipeline`
2. Check database connectivity: `psql -h $DB_HOST -U neutron -d neutron -c '\l'`
3. Check network connectivity

**Resolution:**
- If workers down: Restart Temporal workers
- If database down: Failover to replica
- If network issue: Fix network, update DNS

**Prevention:**
- Health checks on all services
- Automatic failover for database
- Multi-region deployment for critical services

---

## Scaling Guidelines

### Vertical Scaling

**Database:**
- Start: 4 vCPU, 16GB RAM (handles ~500 audits/sec)
- Medium: 8 vCPU, 32GB RAM (handles ~2000 audits/sec)
- Large: 16 vCPU, 64GB RAM (handles ~5000 audits/sec)

**Temporal Workers:**
- Start: 2 vCPU, 8GB RAM per worker
- Scale: Add workers (not increase worker size)

### Horizontal Scaling

**Read Replicas:**
- Add 1 replica per 1000 audit queries/sec
- Use connection pooler (pgBouncer) to distribute load

**Temporal Workers:**
- Add workers to handle increased validation load
- Each worker handles ~100 concurrent validations

**Caching Layer:**
- Add Redis for aggregate statistics (optional)
- Cache audit query results (1 min TTL)

### Capacity Planning

**Formula:**
```
Required DB IOPS = (Validations/sec × 2 writes/validation) + (Queries/sec × 5 reads/query)
Required Workers = Validations/sec ÷ 100
Required Storage = Audits/day × 2KB × 90 days retention
```

**Example:**
- 10,000 validations/sec
- 1,000 queries/sec
- IOPS: 10,000 × 2 + 1,000 × 5 = 25,000 IOPS
- Workers: 10,000 ÷ 100 = 100 workers
- Storage: 10,000 × 86,400 × 2KB × 90 = 155GB

---

## Security Best Practices

### 1. Database Security

**Access Control:**
```sql
-- SENTINEL service account (write + read)
CREATE ROLE sentinel_service WITH LOGIN PASSWORD 'secure_password';
GRANT INSERT, SELECT ON compliance_audits TO sentinel_service;
GRANT USAGE, SELECT ON SEQUENCE compliance_audits_id_seq TO sentinel_service;

-- Analytics account (read-only)
CREATE ROLE sentinel_analytics WITH LOGIN PASSWORD 'secure_password';
GRANT SELECT ON compliance_audits TO sentinel_analytics;

-- No DELETE or UPDATE permissions (immutable audit trail)
```

**Encryption:**
- Use SSL/TLS for all connections (`sslmode=require`)
- Encrypt database at rest (LUKS, AWS EBS encryption)
- Rotate credentials quarterly

### 2. Audit Log Integrity

**Tamper Detection:**
```python
# Add integrity verification
def verify_audit_integrity():
    """Verify no gaps in audit log sequence"""
    cursor.execute("""
        SELECT id FROM compliance_audits
        ORDER BY id
    """)
    ids = [row[0] for row in cursor.fetchall()]

    # Check for gaps
    expected = set(range(ids[0], ids[-1] + 1))
    actual = set(ids)
    missing = expected - actual

    if missing:
        raise IntegrityError(f"Missing audit IDs: {missing}")
```

**Hash Verification:**
```python
# Verify output hash matches logged hash
def verify_output_hash(audit_id, original_output):
    audit = logger.get_audit_by_id(audit_id)
    expected_hash = audit['agent_output_hash']

    actual_hash = hashlib.sha256(
        json.dumps({
            "content": original_output.content,
            "metadata": original_output.metadata,
            "timestamp": original_output.timestamp.isoformat()
        }, sort_keys=True).encode()
    ).hexdigest()

    assert expected_hash == actual_hash, "Hash mismatch - tampered output"
```

### 3. Secrets Management

**Do NOT:**
- ❌ Hardcode database passwords
- ❌ Store credentials in environment variables (prod)
- ❌ Commit secrets to Git

**Do:**
- ✅ Use secret management (Vault, AWS Secrets Manager)
- ✅ Rotate secrets regularly
- ✅ Use IAM roles (AWS RDS IAM authentication)

**Example:**
```python
# Use AWS Secrets Manager
import boto3
import json

def get_db_connection():
    client = boto3.client('secretsmanager')
    secret = client.get_secret_value(SecretId='sentinel/database')
    creds = json.loads(secret['SecretString'])

    return psycopg2.connect(
        host=creds['host'],
        user=creds['username'],
        password=creds['password'],
        dbname='neutron',
        sslmode='require'
    )
```

---

## Regulatory Compliance

### LGPD Compliance

**Article 18 - Right to Explanation:**
- ✅ Enforcement: Blocking guardrail (severity="block")
- ✅ Audit trail: All decisions logged with explanations
- ✅ Proof: Query audit logs filtered by `regulation='LGPD'`

**Article 20 - Data Portability:**
- ✅ Enforcement: Warning guardrail (severity="warn")
- ✅ Audit trail: All portability violations logged
- ✅ Proof: Exportable format documented in metadata

### GDPR Readiness (Phase 2)

**Planned:**
- Article 22: Automated decision-making
- Article 17: Right to erasure
- Article 15: Right to access

### Audit Preparation

**For External Audits:**

1. **Generate Compliance Report**
```sql
-- Last 90 days compliance summary
SELECT
    regulation,
    COUNT(*) as total_audits,
    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as compliant,
    ROUND(100.0 * SUM(CASE WHEN passed THEN 1 ELSE 0 END) / COUNT(*), 2) as compliance_rate
FROM compliance_audits
WHERE timestamp >= NOW() - INTERVAL '90 days'
GROUP BY regulation;
```

2. **Export Audit Logs**
```bash
# Export to CSV for auditor review
psql -U neutron -d neutron -c \
  "COPY (SELECT * FROM compliance_audits WHERE regulation = 'LGPD' ORDER BY timestamp DESC LIMIT 10000) TO STDOUT WITH CSV HEADER" \
  > lgpd_audit_logs.csv
```

3. **Integrity Verification**
```python
# Verify no tampering
verify_audit_integrity()
print("✅ Audit log integrity verified")
```

---

## Team Responsibilities

### Engineering Team

**Responsibilities:**
- Implement SENTINEL in new features
- Monitor performance metrics
- Respond to incidents (on-call rotation)
- Maintain documentation

**SLAs:**
- P0 (production down): 15 min response time
- P1 (degraded performance): 1 hour response time
- P2 (non-critical): Next business day

### ML Team

**Responsibilities:**
- Ensure models generate explanations
- Set explanation quality scores
- Test models against guardrails before deployment
- Respond to blocking violations

**SLAs:**
- Fix blocking models within 4 hours
- Improve explanation quality within 1 week

### Compliance Team

**Responsibilities:**
- Define guardrail requirements
- Review violation trends
- Prepare for external audits
- Update regulations (LGPD, GDPR, AI Act)

**SLAs:**
- Review weekly compliance reports
- Update guardrails within 2 weeks of regulation changes

### DevOps Team

**Responsibilities:**
- Maintain database infrastructure
- Monitor system health
- Scale resources as needed
- Database backups and disaster recovery

**SLAs:**
- 99.9% uptime for audit logging
- < 1 hour RTO (recovery time objective)
- < 5 min RPO (recovery point objective)

---

## Quick Reference

### Common Commands

```bash
# Check compliance rate
psql -U neutron -d neutron -c "SELECT regulation, ROUND(100.0 * SUM(CASE WHEN passed THEN 1 ELSE 0 END) / COUNT(*), 2) as compliance_rate FROM compliance_audits WHERE timestamp >= NOW() - INTERVAL '7 days' GROUP BY regulation;"

# Find recent violations
psql -U neutron -d neutron -c "SELECT timestamp, guardrail_name, details FROM compliance_audits WHERE passed = false ORDER BY timestamp DESC LIMIT 10;"

# Check database performance
psql -U neutron -d neutron -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Run demo
python scripts/demo_sentinel.py --demo all

# Run tests
pytest tests/compliance/ -v

# Check audit log integrity
python -c "from neutron.compliance.audit_logger import AuditLogger; AuditLogger().verify_integrity()"
```

### Environment Variables

```bash
# Production
export DATABASE_URL="postgresql://sentinel_service:password@db.example.com:5432/neutron?sslmode=require"
export TEMPORAL_HOST="temporal.example.com:7233"
export LOG_LEVEL="INFO"

# Staging
export DATABASE_URL="postgresql://sentinel_service:password@db-staging.example.com:5432/neutron?sslmode=require"
export TEMPORAL_HOST="temporal-staging.example.com:7233"
export LOG_LEVEL="DEBUG"
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-16
**Status**: Production Ready

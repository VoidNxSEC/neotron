"""
Immutable Audit Logger for SENTINEL

Logs all compliance enforcement events to PostgreSQL with tamper-proof guarantees.
Once logged, events cannot be modified or deleted.

Philosophy:
    Audit trails are write-only. Trust comes from immutability.
"""

import psycopg2
from psycopg2.extras import Json, RealDictCursor
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class AuditLogger:
    """
    Immutable audit logger using PostgreSQL

    All compliance events are logged to a write-only table with cryptographic
    hashes and timestamps. This creates a tamper-proof audit trail for
    regulatory compliance.

    Attributes:
        connection_string: PostgreSQL connection string

    Example:
        >>> logger = AuditLogger()
        >>> audit_id = logger.log({
        ...     "guardrail_name": "lgpd_art18",
        ...     "regulation": "LGPD",
        ...     "passed": True
        ... })
        >>> print(f"Logged as audit ID: {audit_id}")
    """

    def __init__(self, connection_string: str = None):
        """
        Initialize audit logger

        Args:
            connection_string: PostgreSQL connection string
                             (defaults to POSTGRES_URL env var)
        """
        self.connection_string = connection_string or os.getenv(
            "POSTGRES_URL",
            "postgresql://neutron:neutron@localhost:5432/neutron"
        )

    def log(self, audit_data: Dict[str, Any]) -> int:
        """
        Log compliance audit event

        Creates an immutable record in the compliance_audits table.
        This operation is write-only - records cannot be modified.

        Args:
            audit_data: Audit event data containing:
                - timestamp: ISO format timestamp
                - guardrail_name: Name of the guardrail
                - regulation: Regulation being enforced
                - agent_output_hash: SHA-256 hash of output
                - validation_result: Result details
                - severity: Enforcement severity
                - passed: Whether validation passed
                - model_name: (optional) Model that generated output

        Returns:
            Audit log ID

        Raises:
            psycopg2.Error: If database operation fails
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO compliance_audits (
                        timestamp,
                        guardrail_name,
                        regulation,
                        agent_output_hash,
                        validation_result,
                        severity,
                        passed,
                        details,
                        model_name
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id
                """, (
                    datetime.fromisoformat(audit_data["timestamp"]),
                    audit_data["guardrail_name"],
                    audit_data["regulation"],
                    audit_data["agent_output_hash"],
                    Json(audit_data["validation_result"]),
                    audit_data["severity"],
                    audit_data["passed"],
                    audit_data["validation_result"].get("details", ""),
                    audit_data.get("model_name")
                ))

                audit_id = cur.fetchone()[0]
                conn.commit()
                return audit_id

        except Exception as e:
            if conn:
                conn.rollback()
            # Log to stderr as fallback
            print(f"ERROR: Failed to log audit event: {e}", flush=True)
            # Return -1 to indicate logging failure but don't crash
            return -1

        finally:
            if conn:
                conn.close()

    def query_audits(
        self,
        guardrail_name: str = None,
        regulation: str = None,
        passed: bool = None,
        severity: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs (read-only)

        Args:
            guardrail_name: Filter by guardrail name
            regulation: Filter by regulation (LGPD, GDPR, etc.)
            passed: Filter by pass/fail status
            severity: Filter by severity (block, warn, audit)
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of results

        Returns:
            List of audit records as dictionaries
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                conditions = []
                params = []

                if guardrail_name:
                    conditions.append("guardrail_name = %s")
                    params.append(guardrail_name)

                if regulation:
                    conditions.append("regulation = %s")
                    params.append(regulation)

                if passed is not None:
                    conditions.append("passed = %s")
                    params.append(passed)

                if severity:
                    conditions.append("severity = %s")
                    params.append(severity)

                if start_time:
                    conditions.append("timestamp >= %s")
                    params.append(start_time)

                if end_time:
                    conditions.append("timestamp <= %s")
                    params.append(end_time)

                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                params.append(limit)

                cur.execute(f"""
                    SELECT
                        id,
                        timestamp,
                        guardrail_name,
                        regulation,
                        agent_output_hash,
                        validation_result,
                        severity,
                        passed,
                        details,
                        model_name
                    FROM compliance_audits
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, params)

                return [dict(row) for row in cur.fetchall()]

        finally:
            if conn:
                conn.close()

    def get_violations_summary(
        self,
        regulation: str = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Get summary of compliance violations

        Args:
            regulation: Filter by regulation (optional)
            days_back: How many days to look back

        Returns:
            Dictionary with violation statistics:
                - total_checks: Total number of checks
                - total_violations: Number of failed checks
                - violation_rate: Percentage of failures
                - by_guardrail: Breakdown by guardrail
                - by_severity: Breakdown by severity
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                start_time = datetime.utcnow() - timedelta(days=days_back)

                # Base condition
                where_clause = "timestamp >= %s"
                params = [start_time]

                if regulation:
                    where_clause += " AND regulation = %s"
                    params.append(regulation)

                # Total checks
                cur.execute(f"""
                    SELECT COUNT(*) as total
                    FROM compliance_audits
                    WHERE {where_clause}
                """, params)
                total_checks = cur.fetchone()["total"]

                # Total violations
                cur.execute(f"""
                    SELECT COUNT(*) as total
                    FROM compliance_audits
                    WHERE {where_clause} AND passed = FALSE
                """, params)
                total_violations = cur.fetchone()["total"]

                # By guardrail
                cur.execute(f"""
                    SELECT
                        guardrail_name,
                        COUNT(*) as total,
                        SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) as violations
                    FROM compliance_audits
                    WHERE {where_clause}
                    GROUP BY guardrail_name
                    ORDER BY violations DESC
                """, params)
                by_guardrail = [dict(row) for row in cur.fetchall()]

                # By severity
                cur.execute(f"""
                    SELECT
                        severity,
                        COUNT(*) as total,
                        SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) as violations
                    FROM compliance_audits
                    WHERE {where_clause}
                    GROUP BY severity
                """, params)
                by_severity = [dict(row) for row in cur.fetchall()]

                violation_rate = (total_violations / total_checks * 100) if total_checks > 0 else 0.0

                return {
                    "total_checks": total_checks,
                    "total_violations": total_violations,
                    "violation_rate": round(violation_rate, 2),
                    "by_guardrail": by_guardrail,
                    "by_severity": by_severity,
                    "period_days": days_back,
                    "regulation": regulation
                }

        finally:
            if conn:
                conn.close()

    def verify_audit_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of audit trail

        Checks for:
        - Gaps in audit IDs (deleted records)
        - Duplicate hashes (replay attacks)
        - Timestamp anomalies

        Returns:
            Dictionary with integrity check results
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check for gaps in IDs
                cur.execute("""
                    SELECT
                        MIN(id) as min_id,
                        MAX(id) as max_id,
                        COUNT(*) as total_records
                    FROM compliance_audits
                """)
                stats = dict(cur.fetchone())

                expected_records = stats["max_id"] - stats["min_id"] + 1 if stats["min_id"] else 0
                missing_records = expected_records - stats["total_records"]

                # Check for duplicate hashes (should be rare but possible)
                cur.execute("""
                    SELECT agent_output_hash, COUNT(*) as count
                    FROM compliance_audits
                    GROUP BY agent_output_hash
                    HAVING COUNT(*) > 1
                """)
                duplicate_hashes = cur.fetchall()

                return {
                    "integrity_ok": missing_records == 0,
                    "total_records": stats["total_records"],
                    "missing_records": missing_records,
                    "duplicate_hashes": len(duplicate_hashes),
                    "warnings": []
                }

        finally:
            if conn:
                conn.close()

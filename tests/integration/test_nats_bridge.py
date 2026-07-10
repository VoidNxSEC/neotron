"""
Integration tests for NATS Event Bridge (Track A4).

Validates the complete Neotron → NATS → SPECTRE event pipeline:

  A4.1 — Event type registry completeness
  A4.2 — Dataclass serialization roundtrip (Python ↔ JSON)
  A4.3 — Bridge encode/decode correctness
  A4.4 — Schema validation for known/unknown event types
  A4.5 — NATS publish/subscribe (mocked — no live NATS required)
  A4.6 — EventChannel interface
  A4.7 — Request-reply pattern (mocked)
  A4.8 — Health check when NATS is unavailable
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# A4.1 — Event type registry
# ---------------------------------------------------------------------------


def test_registry_has_all_required_types():
    """Verify all essential event types are registered."""
    from neutron.events.bridge import EVENT_REGISTRY

    required = [
        "sentinel_check",
        "sentinel_violation",
        "bastion_enforce",
        "cortex_consensus",
        "siem_export",
        "audit_log",
        "license_verify_request",
        "license_verify_result",
        "spectre_health",
        "spectre_secret_rotation",
    ]
    for name in required:
        assert name in EVENT_REGISTRY, f"Missing event type: {name}"
        info = EVENT_REGISTRY[name]
        assert info.subject, f"{name} has no subject"
        assert info.description, f"{name} has no description"


def test_registry_filter_by_source():
    """Verify source filtering works."""
    from neutron.events.bridge import list_event_types

    neotron_events = list_event_types("neotron")
    spectre_events = list_event_types("spectre")
    ip_guard_events = list_event_types("ip-guard")

    assert len(neotron_events) >= 6  # SENTINEL, BASTION, CORTEX, SIEM, audit, license_request
    assert len(spectre_events) >= 2  # health, secret_rotation
    assert len(ip_guard_events) >= 1  # license_verify_result

    # All sources are valid
    for e in neotron_events:
        assert e.source == "neotron"
    for e in spectre_events:
        assert e.source == "spectre"


def test_subject_map_consistency():
    """Verify subject-to-type mappings match the registry."""
    from neutron.events.bridge import _SUBJECT_MAP, EVENT_REGISTRY, get_event_type_for_subject

    assert len(_SUBJECT_MAP) == len(EVENT_REGISTRY)

    for name, info in EVENT_REGISTRY.items():
        mapped = get_event_type_for_subject(info.subject)
        assert mapped == name, f"Subject {info.subject} maps to {mapped}, expected {name}"


# ---------------------------------------------------------------------------
# A4.2 — Dataclass roundtrip (Python ↔ JSON)
# ---------------------------------------------------------------------------


def test_compliance_event_roundtrip():
    """ComplianceEvent survives dict roundtrip."""
    from neutron.events.bridge import ComplianceEvent

    original = ComplianceEvent(
        audit_id=42,
        guardrail_name="lgpd_consent",
        regulation="LGPD",
        severity="high",
        passed=False,
        confidence=0.95,
        agent_output_hash="abc123",
        details="User did not provide consent",
        agent_id="agent-1",
        risk_score=0.8,
        reputation=0.9,
        metadata={"region": "BR"},
    )
    data = original.to_dict()
    restored = ComplianceEvent.from_dict(data)

    assert restored.audit_id == original.audit_id
    assert restored.guardrail_name == original.guardrail_name
    assert restored.regulation == original.regulation
    assert restored.severity == original.severity
    assert restored.passed == original.passed
    assert restored.confidence == original.confidence
    assert restored.agent_output_hash == original.agent_output_hash
    assert restored.details == original.details
    assert restored.agent_id == original.agent_id
    assert restored.risk_score == original.risk_score
    assert restored.reputation == original.reputation
    assert restored.metadata == original.metadata
    assert restored.timestamp  # auto-generated
    assert not original.is_violation() or not restored.passed


def test_compliance_event_is_violation():
    """is_violation() correctly identifies violations."""
    from neutron.events.bridge import ComplianceEvent

    # Not a violation — passed
    ok = ComplianceEvent(passed=True, severity="block")
    assert not ok.is_violation()

    # Violation — failed + block
    violation = ComplianceEvent(passed=False, severity="block")
    assert violation.is_violation()

    # Violation — failed + critical
    violation2 = ComplianceEvent(passed=False, severity="critical")
    assert violation2.is_violation()

    # Violation — failed + high
    violation3 = ComplianceEvent(passed=False, severity="high")
    assert violation3.is_violation()

    # Not a violation — failed but medium
    medium = ComplianceEvent(passed=False, severity="medium")
    assert not medium.is_violation()


def test_license_verify_request_roundtrip():
    """LicenseVerifyRequest survives dict roundtrip."""
    from neutron.events.bridge import LicenseVerifyRequest

    original = LicenseVerifyRequest(
        flake_path="/path/to/flake.nix",
        package_name="python3",
        store_hash="sha256-abc123",
    )
    data = original.to_dict()
    restored = LicenseVerifyRequest.from_dict(data)

    assert restored.flake_path == original.flake_path
    assert restored.package_name == original.package_name
    assert restored.store_hash == original.store_hash
    assert restored.request_id  # auto-generated UUID
    assert restored.timestamp  # auto-generated


def test_license_verify_result_roundtrip():
    """LicenseVerifyResult survives dict roundtrip."""
    from neutron.events.bridge import LicenseVerifyResult

    original = LicenseVerifyResult(
        request_id="req-001",
        package_name="python3",
        store_hash="sha256-abc",
        license_spdx="MIT",
        token_id=42,
        compliant=True,
        proof_hash="0xdeadbeef",
        tx_hash="0xcafe1234",
        errors=[],
    )
    data = original.to_dict()
    restored = LicenseVerifyResult.from_dict(data)

    assert restored.request_id == original.request_id
    assert restored.license_spdx == original.license_spdx
    assert restored.token_id == original.token_id
    assert restored.compliant is True
    assert restored.errors == []


def test_siem_export_event_roundtrip():
    """SIEMExportEvent survives dict roundtrip."""
    from neutron.events.bridge import SIEMExportEvent

    original = SIEMExportEvent(
        format="cef",
        target="file",
        event_count=100,
        bytes_written=4096,
        filepath="/var/log/siem/neotron-cef.log",
        errors=["timeout on event 42"],
    )
    data = original.to_dict()
    restored = SIEMExportEvent.from_dict(data)

    assert restored.format == "cef"
    assert restored.target == "file"
    assert restored.event_count == 100
    assert restored.bytes_written == 4096
    assert restored.errors == ["timeout on event 42"]


def test_spectre_health_event_roundtrip():
    """SpectreHealthEvent survives dict roundtrip."""
    from neutron.events.bridge import SpectreHealthEvent

    original = SpectreHealthEvent(
        status="healthy",
        version="2.0.0",
        uptime_seconds=7200,
        connected_clients=5,
    )
    data = original.to_dict()
    restored = SpectreHealthEvent.from_dict(data)

    assert restored.status == "healthy"
    assert restored.version == "2.0.0"
    assert restored.uptime_seconds == 7200
    assert restored.connected_clients == 5


# ---------------------------------------------------------------------------
# A4.3 — Bridge encode/decode
# ---------------------------------------------------------------------------


def test_decode_event_bytes():
    """decode_event handles raw bytes payloads."""
    from neutron.events.bridge import ComplianceEvent, decode_event

    payload = json.dumps(
        {
            "audit_id": 123,
            "guardrail_name": "test_guard",
            "regulation": "GDPR",
            "severity": "critical",
            "passed": False,
        }
    ).encode()

    event = decode_event("neotron.compliance.sentinel.v1", payload)
    assert isinstance(event, ComplianceEvent)
    assert event.audit_id == 123
    assert event.guardrail_name == "test_guard"


def test_decode_event_string():
    """decode_event handles string payloads."""
    from neutron.events.bridge import ComplianceEvent, decode_event

    payload = json.dumps({"audit_id": 456, "guardrail_name": "test_str"})

    event = decode_event("neotron.compliance.sentinel.v1", payload)
    assert isinstance(event, ComplianceEvent)
    assert event.audit_id == 456


def test_decode_event_dict():
    """decode_event handles pre-parsed dict payloads."""
    from neutron.events.bridge import ComplianceEvent, decode_event

    payload = {"audit_id": 789, "guardrail_name": "test_dict"}

    event = decode_event("neotron.compliance.sentinel.v1", payload)
    assert isinstance(event, ComplianceEvent)
    assert event.audit_id == 789


def test_decode_event_unknown_subject():
    """decode_event returns None for unmapped subjects."""
    from neutron.events.bridge import decode_event

    result = decode_event("unknown.subject.v1", b"{}")
    assert result is None


def test_decode_event_license_request():
    """decode_event correctly routes license verification subjects."""
    from neutron.events.bridge import LicenseVerifyRequest, decode_event

    payload = json.dumps(
        {
            "flake_path": "/test/flake.nix",
            "package_name": "rustc",
            "store_hash": "sha256-test",
        }
    ).encode()

    event = decode_event("ipguard.license.verify.v1", payload)
    assert isinstance(event, LicenseVerifyRequest)
    assert event.package_name == "rustc"


def test_decode_event_license_result():
    """decode_event correctly routes license result subjects."""
    from neutron.events.bridge import LicenseVerifyResult, decode_event

    payload = json.dumps(
        {
            "request_id": "req-xyz",
            "license_spdx": "Apache-2.0",
            "token_id": 10,
            "compliant": True,
        }
    ).encode()

    event = decode_event("ipguard.license.result.v1", payload)
    assert isinstance(event, LicenseVerifyResult)
    assert event.license_spdx == "Apache-2.0"


def test_encode_event():
    """encode_event produces valid JSON bytes."""
    from neutron.events.bridge import ComplianceEvent, encode_event

    event = ComplianceEvent(audit_id=1, guardrail_name="encoder_test")
    result = encode_event(event)

    assert isinstance(result, bytes)
    decoded = json.loads(result.decode())
    assert decoded["audit_id"] == 1
    assert decoded["guardrail_name"] == "encoder_test"


def test_encode_event_pretty():
    """encode_event with pretty=True produces indented output."""
    from neutron.events.bridge import ComplianceEvent, encode_event

    event = ComplianceEvent(audit_id=1, guardrail_name="pretty_test")
    result = encode_event(event, pretty=True)

    assert b"\n  " in result  # pretty-print includes newlines + indentation


# ---------------------------------------------------------------------------
# A4.4 — Schema validation
# ---------------------------------------------------------------------------


def test_validate_known_event():
    """validate_event passes for valid payloads."""
    from neutron.events.bridge import validate_event

    errors = validate_event(
        "sentinel_check",
        {
            "audit_id": 1,
            "guardrail_name": "test",
            "passed": True,
        },
    )
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_validate_unknown_event():
    """validate_event reports unknown event types."""
    from neutron.events.bridge import validate_event

    errors = validate_event("nonexistent_type", {})
    assert len(errors) >= 1
    assert "Unknown" in errors[0]


# ---------------------------------------------------------------------------
# A4.5 — NATS publish/subscribe (mocked)
# ---------------------------------------------------------------------------


async def test_publish_when_nats_unavailable():
    """publish returns False when NATS is not available."""

    from neutron.events import publish

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=None)):
        result = await publish("test.subject", {"key": "value"})
        assert result is False


async def test_publish_when_nats_available():
    """publish returns True when NATS accepts the message."""

    from neutron.events import publish

    mock_nc = MagicMock()
    mock_nc.publish = AsyncMock(return_value=None)

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        result = await publish("neotron.compliance.sentinel.v1", {"audit_id": 1})
        assert result is True
        mock_nc.publish.assert_called_once()


async def test_subscribe_when_nats_unavailable():
    """subscribe returns None when NATS is not available."""

    from neutron.events import subscribe

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=None)):
        result = await subscribe("test.>", AsyncMock())
        assert result is None


async def test_subscribe_calls_callback():
    """subscribe invokes the callback when a message arrives."""

    from neutron.events import subscribe

    mock_nc = MagicMock()
    received = []

    async def capture_sub(subject, cb=None, queue=None):
        received.append(("subscribe", subject, cb, queue))

        # Simulate a message arriving
        import json

        msg = MagicMock()
        msg.data = json.dumps({"audit_id": 42, "guardrail_name": "test_event"}).encode()
        await cb(msg)
        return MagicMock()

    mock_nc.subscribe = capture_sub

    callback_messages = []

    async def my_callback(payload):
        callback_messages.append(payload)

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        sub = await subscribe("neotron.compliance.sentinel.v1", my_callback, "workers")

    assert sub is not None
    assert len(received) == 1
    assert received[0][0] == "subscribe"
    assert received[0][3] == "workers"  # queue group

    # Callback should have been invoked with the decoded message
    assert len(callback_messages) == 1
    assert callback_messages[0]["audit_id"] == 42
    assert callback_messages[0]["guardrail_name"] == "test_event"


# ---------------------------------------------------------------------------
# A4.6 — EventChannel interface
# ---------------------------------------------------------------------------


async def test_event_channel_send():
    """EventChannel.send publishes to the correct subject."""

    from neutron.events import EventChannel

    mock_nc = MagicMock()
    mock_nc.publish = AsyncMock(return_value=None)

    channel = EventChannel("neotron.compliance.sentinel.v1")

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        result = await channel.send({"audit_id": 999})
        assert result is True
        mock_nc.publish.assert_called_once()


def test_event_channel_repr():
    """EventChannel has a readable repr."""
    from neutron.events import EventChannel

    channel = EventChannel("test.subject", "my-queue")
    assert "test.subject" in repr(channel)


# ---------------------------------------------------------------------------
# A4.7 — Request-reply pattern
# ---------------------------------------------------------------------------


async def test_request_when_nats_unavailable():
    """request returns None when NATS is not available."""

    from neutron.events import request

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=None)):
        result = await request("test.request", {"q": "test"})
        assert result is None


async def test_request_receives_reply():
    """request returns decoded reply when NATS responds."""

    from neutron.events import request

    mock_nc = MagicMock()
    reply_msg = MagicMock()
    reply_msg.data = json.dumps({"token_id": 42, "compliant": True}).encode()
    mock_nc.request = AsyncMock(return_value=reply_msg)

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        result = await request(
            "ipguard.license.verify.v1",
            {
                "flake_path": "/test/flake.nix",
                "package_name": "rustc",
            },
        )

    assert result is not None
    assert result["token_id"] == 42
    assert result["compliant"] is True


async def test_request_timeout():
    """request returns None on timeout."""

    from neutron.events import request

    mock_nc = MagicMock()
    mock_nc.request = AsyncMock(side_effect=TimeoutError())

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        result = await request("slow.service", {}, timeout=0.1)
        assert result is None


# ---------------------------------------------------------------------------
# A4.8 — Health check
# ---------------------------------------------------------------------------


async def test_health_unavailable():
    """health returns unavailable when NATS is not connected."""

    from neutron.events import health

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=None)):
        result = await health()
        assert result["status"] == "unavailable"
        assert result["connected"] is False


async def test_health_connected():
    """health returns healthy when NATS is connected."""

    from neutron.events import health

    mock_nc = MagicMock()
    mock_nc.is_connected = True
    mock_nc.server_info = {"version": "2.10.0", "server_name": "test-server"}

    with patch("neutron.events.get_connection", new=AsyncMock(return_value=mock_nc)):
        result = await health()
        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert result["server_info"]["version"] == "2.10.0"


# ---------------------------------------------------------------------------
# A4.9 — CLI group registration
# ---------------------------------------------------------------------------


def test_event_group_is_click_group():
    """event_group is a click.Group with correct name."""
    from neutron.events.cli_commands import event_group

    assert event_group.name == "event"


def test_event_group_commands_registered():
    """event_group has all expected subcommands."""
    from neutron.events.cli_commands import event_group

    command_names = list(event_group.commands.keys())
    assert "list" in command_names
    assert "emit" in command_names
    assert "subscribe" in command_names
    assert "health" in command_names


# ---------------------------------------------------------------------------
# A4.10 — Namespace prefixing
# ---------------------------------------------------------------------------


def test_namespace_prefixing(monkeypatch):
    """Subjects are prefixed when NATS_NAMESPACE is set."""
    monkeypatch.setenv("NATS_NAMESPACE", "staging")
    # Re-import to pick up env var
    import importlib

    import neutron.events

    importlib.reload(neutron.events)

    assert neutron.events.NATS_NAMESPACE == "staging"
    assert neutron.events._ns("test.subject") == "staging.test.subject"

    # Cleanup
    monkeypatch.delenv("NATS_NAMESPACE")
    importlib.reload(neutron.events)


def test_no_namespace_prefixing(monkeypatch):
    """Subjects are not prefixed when NATS_NAMESPACE is empty."""
    monkeypatch.delenv("NATS_NAMESPACE", raising=False)
    import importlib

    import neutron.events

    importlib.reload(neutron.events)

    assert neutron.events.NATS_NAMESPACE == ""
    assert neutron.events._ns("test.subject") == "test.subject"

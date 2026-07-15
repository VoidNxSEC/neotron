"""
NATS Event Bridge CLI — `neotron event {emit,subscribe,list,health}`.

Provides CLI access to the NATS event bus for debugging, testing,
and operational control of the Neotron ↔ SPECTRE event bridge.

Examples:
  neotron event list                          # List all registered event types
  neotron event list --source spectre         # List only SPECTRE events
  neotron event emit sentinel_check           # Emit a test SENTINEL event
  neotron event emit sentinel_check --data '{"audit_id": 42, ...}'
  neotron event subscribe sentinel_check      # Subscribe and print events
  neotron event health                        # Check NATS bridge health
"""

from __future__ import annotations

import asyncio
import json
import time

import click

from neutron.events.bridge import EVENT_REGISTRY, list_event_types

# ============================================================================
# Event Group
# ============================================================================


@click.group(name="event")
def event_group():
    """🔗 NATS Event Bridge — emitir, subscrever e inspecionar eventos.

    O event bridge conecta Neotron ao ecossistema NEXUS via NATS:
      - Neotron → SPECTRE (compliance events)
      - Neotron → IP Guard (license verification)
      - SPECTRE → Neotron (health, secrets, responses)
      - IP Guard → Neotron (verification results)

    Configuração via variáveis de ambiente:
      NATS_URL      URL do servidor NATS (default: nats://localhost:4222)
      NATS_TOKEN    Token de autenticação (opcional)
      NATS_NAMESPACE Prefixo de namespace nos subjects (opcional)
    """
    pass


# ============================================================================
# LIST
# ============================================================================


@event_group.command(name="list")
@click.option("--source", "-s", default=None, help="Filtrar por source: neotron, spectre, ip-guard")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def event_list(source: str | None, as_json: bool):
    """📋 Listar todos os tipos de eventos registrados no bridge."""
    events = list_event_types(source)

    if as_json:
        data = [
            {
                "name": e.name,
                "subject": e.subject,
                "version": e.version.value,
                "description": e.description,
                "source": e.source,
            }
            for e in events
        ]
        click.echo(json.dumps(data, indent=2, default=str))
        return

    click.secho(f"\n📋 Event Types Registered ({len(events)} total)", fg="blue", bold=True)
    if source:
        click.secho(f"   Filtered by source: {source}", fg="yellow")

    click.echo()
    click.echo(f"  {'Name':<32} {'Subject':<48} {'Source':<12}")
    click.echo(f"  {'─' * 32} {'─' * 48} {'─' * 12}")

    for e in events:
        click.echo(f"  {e.name:<32} {e.subject:<48} {e.source:<12}")

    click.echo()
    click.secho(f"  Total: {len(events)} event types", fg="green")


# ============================================================================
# EMIT
# ============================================================================


@event_group.command(name="emit")
@click.argument("event_type", required=True)
@click.option(
    "--data", "-d", default=None, help="JSON payload (inline). If omitted, a test event is created."
)
@click.option("--file", "-f", default=None, type=click.Path(exists=True), help="JSON file payload")
@click.option("--count", "-n", default=1, help="Number of events to emit (for load testing)")
@click.option("--interval", "-i", default=0.0, help="Interval between events in seconds")
def event_emit(event_type: str, data: str | None, file: str | None, count: int, interval: float):
    """📤 Emitir um evento para o NATS bridge.

    EVENT_TYPE: Tipo do evento (use 'neotron event list' para ver os disponíveis)

    Exemplos:
      neotron event emit sentinel_check
      neotron event emit sentinel_check --data '{"audit_id": 42, "passed": true}'
      neotron event emit sentinel_check -n 100 -i 0.1
      neotron event emit license_verify_request -f payload.json
    """
    # Load payload
    if file:
        payload = json.loads(open(file).read())
    elif data:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            click.secho("❌ Invalid JSON payload", fg="red")
            return
    else:
        # Generate a test event
        payload = _generate_test_event(event_type)

    # Validate event type
    if event_type not in EVENT_REGISTRY:
        click.secho(f"❌ Unknown event type: {event_type}", fg="red")
        click.echo("   Use 'neotron event list' to see available types.")
        return

    info = EVENT_REGISTRY[event_type]

    click.secho(f"\n📤 Emitting {count} event(s) → {info.subject}\n", fg="blue", bold=True)

    async def _emit():
        from neutron.events import publish

        success = 0
        failed = 0

        for i in range(count):
            ok = await publish(info.subject, payload)
            if ok:
                success += 1
            else:
                failed += 1

            if i < min(3, count):
                payload_preview = json.dumps(payload, default=str)[:120]
                status = "✅" if ok else "❌"
                click.echo(f"  {status} [{i + 1}/{count}] {payload_preview}...")

            if interval > 0 and i < count - 1:
                await asyncio.sleep(interval)

        return success, failed

    try:
        success, failed = asyncio.run(_emit())
    except Exception as e:
        click.secho(f"❌ Emit failed: {e}", fg="red")
        return

    click.echo()
    if failed == 0:
        click.secho(f"✅ All {success} events emitted successfully", fg="green", bold=True)
    else:
        click.secho(
            f"⚠️  {success} emitted, {failed} failed (NATS unavailable?)", fg="yellow", bold=True
        )


# ============================================================================
# SUBSCRIBE
# ============================================================================


@event_group.command(name="subscribe")
@click.argument("event_type", required=True)
@click.option("--count", "-n", default=10, help="Number of events to receive before exiting")
@click.option("--timeout", "-t", default=30.0, help="Max wait time in seconds")
@click.option("--queue", "-q", default=None, help="Queue group name for load balancing")
def event_subscribe(event_type: str, count: int, timeout: float, queue: str | None):
    """📥 Subscrever a um tipo de evento no NATS bridge.

    Escuta eventos em tempo real e imprime no terminal.

    EVENT_TYPE: Tipo do evento (use 'neotron event list' para ver os disponíveis)

    Exemplos:
      neotron event subscribe sentinel_check
      neotron event subscribe sentinel_check -n 5 -t 10
      neotron event subscribe license_verify_result -q workers
    """
    if event_type not in EVENT_REGISTRY:
        click.secho(f"❌ Unknown event type: {event_type}", fg="red")
        click.echo("   Use 'neotron event list' to see available types.")
        return

    info = EVENT_REGISTRY[event_type]

    click.secho(
        f"\n📥 Subscribing to {info.subject}",
        fg="blue",
        bold=True,
    )
    click.echo(f"   Waiting for {count} events (timeout: {timeout}s)...")
    if queue:
        click.echo(f"   Queue group: {queue}")
    click.echo()

    received: list[dict] = []
    stop_event = asyncio.Event()

    async def _handle(msg: dict):
        received.append(msg)
        click.secho(f"  ✅ [{len(received)}] ", fg="green", nl=False)
        payload_preview = json.dumps(msg, default=str)[:100]
        click.echo(payload_preview + ("..." if len(json.dumps(msg, default=str)) > 100 else ""))
        if len(received) >= count:
            stop_event.set()

    async def _subscribe():
        from neutron.events import subscribe

        sub = await subscribe(info.subject, _handle, queue)
        if sub is None:
            click.secho("❌ Failed to subscribe — NATS unavailable", fg="red")
            stop_event.set()
            return

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=timeout)
        except TimeoutError:
            pass
        finally:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    try:
        asyncio.run(_subscribe())
    except KeyboardInterrupt:
        click.echo()

    click.echo()
    if received:
        click.secho(f"✅ Received {len(received)} events", fg="green", bold=True)
    else:
        click.secho(f"⚠️  No events received within {timeout}s", fg="yellow")


# ============================================================================
# HEALTH
# ============================================================================


@event_group.command(name="health")
def event_health():
    """🏥 Verificar saúde do NATS bridge."""
    click.secho("\n🏥 NATS Bridge Health\n", fg="blue", bold=True)

    async def _check():
        from neutron.events import health

        result = await health()
        return result

    try:
        status = asyncio.run(_check())
    except Exception as e:
        click.secho(f"❌ Health check failed: {e}", fg="red")
        return

    # Connection status
    if status["connected"]:
        click.secho("  Connection:        ✅ Connected", fg="green")
    else:
        click.secho("  Connection:        ❌ Not connected", fg="red")

    click.echo(f"  NATS URL:          {status['nats_url']}")
    click.echo(f"  Status:            {status['status']}")
    click.echo(f"  Namespace:         {status.get('namespace', '(none)')}")

    if status.get("server_info"):
        si = status["server_info"]
        click.echo(f"  Server Version:    {si.get('version', 'unknown')}")
        click.echo(f"  Server Name:       {si.get('server_name', 'unknown')}")
        click.echo(f"  Max Payload:       {si.get('max_payload', 'unknown')}")

    click.echo()


# ============================================================================
# Helpers
# ============================================================================


def _generate_test_event(event_type: str) -> dict:
    """Generate a default test payload for an event type."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    base = {
        "timestamp": ts,
        "source": "neotron-cli",
        "subject": EVENT_REGISTRY[event_type].subject,
    }

    event_generators = {
        "sentinel_check": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "test_sentinel",
            "regulation": "LGPD",
            "severity": "info",
            "passed": True,
            "confidence": 0.95,
            "details": "Test event from neotron event emit",
        },
        "sentinel_violation": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "test_violation",
            "regulation": "GDPR",
            "severity": "critical",
            "passed": False,
            "confidence": 0.99,
            "details": "Test violation from neotron event emit",
        },
        "bastion_enforce": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "test_bastion",
            "regulation": "LGPD",
            "severity": "high",
            "passed": True,
            "details": "Test BASTION enforcement",
        },
        "cortex_consensus": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "test_cortex",
            "regulation": "EU AI Act",
            "severity": "medium",
            "passed": True,
            "confidence": 0.88,
            "details": "Test CORTEX consensus",
        },
        "siem_export": lambda: {
            **base,
            "format": "json",
            "target": "file",
            "event_count": 1,
            "bytes_written": 256,
            "filepath": "/var/log/neotron/siem/test.log",
            "timestamp": ts,
        },
        "audit_log": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "test_audit",
            "regulation": "LGPD",
            "severity": "info",
            "passed": True,
        },
        "license_verify_request": lambda: {
            **base,
            "flake_path": "/home/user/project/flake.nix",
            "package_name": "python3",
            "store_hash": "sha256-abc123def456",
        },
        "license_verify_result": lambda: {
            **base,
            "request_id": "test-req-001",
            "package_name": "python3",
            "store_hash": "sha256-abc123def456",
            "license_spdx": "MIT",
            "token_id": 1,
            "compliant": True,
            "proof_hash": "0xdeadbeef",
            "tx_hash": "0xcafe1234",
        },
        "spectre_health": lambda: {
            **base,
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 3600,
            "connected_clients": 3,
        },
        "spectre_secret_rotation": lambda: {
            **base,
            "audit_id": 999,
            "guardrail_name": "secret_rotation",
            "regulation": "SECURITY",
            "severity": "info",
            "passed": True,
        },
    }

    generator = event_generators.get(event_type)
    if generator:
        return generator()
    return base


__all__ = ["event_group"]

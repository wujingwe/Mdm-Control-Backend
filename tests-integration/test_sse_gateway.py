"""Cross-service integration tests: control backend <-> SSE gateway (tmdm-sse).

Boots both services as real subprocesses and exercises the two communication
channels between them:

- **RabbitMQ (backend -> SSE)**: a command published by the backend's own
  producer is consumed by the SSE gateway and delivered to a connected
  device's SSE stream, keyed by the device serial.
- **HTTP (SSE -> backend)**: the gateway forwards device register/report-in
  to the backend with the shared ``X-SSE-SECRET``, queries backend device
  auth before opening an SSE stream, and probes backend liveness for its
  readiness endpoint.

The SSE service lives at ``SSE_SERVICE_PATH`` (default ``~/Projects/tmdm-sse``);
the suite is skipped when that directory or a usable interpreter is missing.
Requires RabbitMQ at ``RABBITMQ_URL`` (same broker both services share).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.domains.devices.models import Device
from app.infra.config.settings import settings
from app.infra.messaging.broker import broker, exchange
from app.infra.messaging.producer import RabbitMQProducer
from app.domains.profiles.schemas.policy import Policy

logger = logging.getLogger(__name__)

BACKEND_REPO = Path(__file__).resolve().parents[1]
SSE_REPO = Path(os.environ.get("SSE_SERVICE_PATH", str(Path.home() / "Projects" / "tmdm-sse")))

SSE_SECRET = "integration-sse-secret"

pytestmark = pytest.mark.skipif(
    not settings.rabbitmq_url,
    reason="RABBITMQ_URL is not configured (.env)",
)


def _serial() -> str:
    return f"ITST-{uuid.uuid4().hex[:10]}"


def _register_payload(serial: str) -> dict:
    """A register body with a certificate that is valid for another year."""
    expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat().replace("+00:00", "Z")
    return {
        "name": f"Device {serial}",
        "osVersion": "Android 14",
        "certificates": [
            {
                "commonName": serial,
                "issuer": "tMDM Integration CA",
                "expiry": expiry,
                "type": "device",
                "fingerprint": "aa:bb:cc:dd",
                "serialNumber": "cert-1",
            }
        ],
    }


def _report_payload() -> dict:
    return {
        "connectionStatus": "Connected",
        "status": "Enrolled",
        "batteryStatus": 87,
        "totalStorage": 128,
        "availableStorage": 100,
        "totalMemory": 8,
        "availableMemory": 4,
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _sse_interpreter(sse_repo: Path) -> str:
    for candidate in (sse_repo / "venv" / "bin" / "python", sse_repo / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _wait_for_ready(url: str, *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return
            last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.3)
    raise AssertionError(f"{url} did not become ready within {timeout:.0f}s ({last_error})")


@dataclass
class ServerCluster:
    backend_url: str
    sse_url: str
    log_dir: Path
    procs: list[subprocess.Popen[bytes]]

    def spawn(self, name: str, argv: list[str], cwd: Path, env: dict[str, str]) -> None:
        log_file = open(self.log_dir / f"{name}.log", "wb")
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.procs.append(proc)

    def shutdown(self) -> None:
        for proc in self.procs:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 10
        for proc in self.procs:
            try:
                proc.wait(timeout=max(0.5, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@pytest.fixture(scope="session")
def sse_repo() -> Path:
    if not (SSE_REPO / "app" / "main.py").exists():
        pytest.skip(f"SSE service not found at {SSE_REPO} (set SSE_SERVICE_PATH)")
    return SSE_REPO


@pytest.fixture(scope="session")
def servers(sse_repo: Path, _migrated_database: None) -> ServerCluster:
    """Boot the backend and SSE gateway as real HTTP servers for the session."""
    backend_port = _free_port()
    sse_port = _free_port()
    backend_url = f"http://127.0.0.1:{backend_port}"
    sse_url = f"http://127.0.0.1:{sse_port}"
    log_dir = Path(tempfile.mkdtemp(prefix="sse-gateway-itest-"))
    cluster = ServerCluster(backend_url, sse_url, log_dir, [])

    backend_env = os.environ.copy()
    backend_env.update(
        {
            "DB_URL": settings.integration_db_url,
            "MOCK_DB": "false",
            "SSE_SECRET": SSE_SECRET,
            "RABBITMQ_URL": settings.rabbitmq_url,
            "PYTHONUNBUFFERED": "1",
        }
    )
    cluster.spawn(
        "backend",
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        cwd=BACKEND_REPO,
        env=backend_env,
    )

    sse_env = os.environ.copy()
    sse_env.update(
        {
            "BACKEND_BASE_URL": backend_url,
            "BACKEND_SHARED_SECRET": SSE_SECRET,
            "RABBIT_URL": settings.rabbitmq_url,
            "RABBIT_INSTANCE_QUEUE_PREFIX": "itest",
            "KEEP_ALIVE_INTERVAL": "2",
            "PYTHONUNBUFFERED": "1",
        }
    )
    cluster.spawn(
        "sse",
        [
            _sse_interpreter(sse_repo),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(sse_port),
        ],
        cwd=sse_repo,
        env=sse_env,
    )

    try:
        _wait_for_ready(f"{backend_url}/health/live", timeout=90)
        _wait_for_ready(f"{backend_url}/health/ready", timeout=30)
        _wait_for_ready(f"{sse_url}/health/live", timeout=90)
        _wait_for_ready(f"{sse_url}/health/ready", timeout=30)
        logger.info("Cross-service servers ready: backend=%s sse=%s (logs: %s)", backend_url, sse_url, log_dir)
        yield cluster
    finally:
        cluster.shutdown()


@pytest_asyncio.fixture
async def started_broker() -> None:
    """Connect the test process's own broker so it can publish like the backend."""
    await broker.start()
    try:
        await broker.declare_exchange(exchange)
        yield
    finally:
        await broker.stop()


async def _register_via_gateway(client: httpx.AsyncClient, serial: str) -> httpx.Response:
    return await client.post(
        f"/api/v1/devices/{serial}/register",
        headers={"X-SSL-Client-Serial": serial},
        json=_register_payload(serial),
    )


async def _open_sse_stream(client: httpx.AsyncClient, serial: str) -> tuple[asyncio.Queue[str], asyncio.Task[None]]:
    """Open an SSE stream and read its lines into a queue.

    Pushes ``__OPEN__`` once the response has started (the SSE generator is
    running and the device serial is bound on RabbitMQ).
    """

    lines: asyncio.Queue[str] = asyncio.Queue()

    async def _read() -> None:
        async with client.stream(
            "GET", f"/api/v1/subscribers/{serial}", headers={"X-SSL-Client-Serial": serial}
        ) as resp:
            assert resp.status_code == 200
            await lines.put("__OPEN__")
            async for line in resp.aiter_lines():
                await lines.put(line)

    task = asyncio.create_task(_read())
    return lines, task


async def _wait_for_line(lines: asyncio.Queue[str], *, token: str, timeout: float = 10.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            line = await asyncio.wait_for(lines.get(), timeout=max(0.05, deadline - time.monotonic()))
        except asyncio.TimeoutError:
            break
        if token in line:
            return line
    raise AssertionError(f"No stream line containing {token!r} within {timeout:.0f}s")


async def _wait_for_sse_event(lines: asyncio.Queue[str], *, kind: str, timeout: float = 10.0) -> str:
    deadline = time.monotonic() + timeout
    event_lines: list[str] = []
    while time.monotonic() < deadline:
        try:
            line = await asyncio.wait_for(lines.get(), timeout=max(0.05, deadline - time.monotonic()))
        except asyncio.TimeoutError:
            break
        if not line:
            text = "\n".join(event_lines)
            event_lines = []
            if f"event: {kind}" in text:
                return text
        elif line.startswith(":"):
            continue
        elif line == "__OPEN__":
            continue
        else:
            event_lines.append(line)
    raise AssertionError(f"No SSE event of kind {kind!r} within {timeout:.0f}s")


async def _backend_device(session, serial: str) -> Device:
    device = (await session.execute(select(Device).where(Device.serial_number == serial))).scalar_one_or_none()
    assert device is not None, f"device {serial} not found in backend DB"
    return device


# ── HTTP forwarding: SSE -> backend ─────────────────────────────────────────


async def test_register_flows_through_gateway_to_backend(servers: ServerCluster, db_session) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        serial = _serial()
        resp = await _register_via_gateway(client, serial)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["serialNumber"] == serial
        assert body["status"] == "Enrolled"

    device = await _backend_device(db_session, serial)
    assert device.status.value == "Enrolled"
    assert device.certificates is not None
    assert device.certificates[0].expiry  # persisted through the gateway


async def test_report_flows_through_gateway_to_backend(servers: ServerCluster, db_session) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        serial = _serial()
        assert (await _register_via_gateway(client, serial)).status_code == 200
        resp = await client.put(
            f"/api/v1/devices/{serial}/report",
            headers={"X-SSL-Client-Serial": serial},
            json=_report_payload(),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["batteryStatus"] == 87

    device = await _backend_device(db_session, serial)
    assert device.battery_status == 87
    assert device.connection_status.value == "Connected"


async def test_sse_readiness_reports_backend_ok(servers: ServerCluster) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["backend"] == "ok"


async def test_sse_connect_rejects_unknown_device(servers: ServerCluster) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        serial = _serial()
        resp = await client.get(f"/api/v1/subscribers/{serial}", headers={"X-SSL-Client-Serial": serial})
        assert resp.status_code == 400


async def test_sse_requires_mtls_header(servers: ServerCluster) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        serial = _serial()
        resp = await client.post(f"/api/v1/devices/{serial}/register", json=_register_payload(serial))
        assert resp.status_code == 403


async def test_backend_rejects_register_without_sse_secret(servers: ServerCluster) -> None:
    async with httpx.AsyncClient(base_url=servers.backend_url, timeout=10.0) as client:
        serial = _serial()
        resp = await client.post(f"/api/v1/devices/{serial}/register", json=_register_payload(serial))
        assert resp.status_code == 401


# ── RabbitMQ delivery: backend -> SSE -> device stream ──────────────────────


async def test_command_published_by_backend_reaches_device_stream(servers: ServerCluster, started_broker: None) -> None:
    async with httpx.AsyncClient(base_url=servers.sse_url, timeout=10.0) as client:
        serial = _serial()
        assert (await _register_via_gateway(client, serial)).status_code == 200

        lines, reader = await _open_sse_stream(client, serial)
        try:
            await _wait_for_line(lines, token="__OPEN__", timeout=10.0)
            await _wait_for_line(lines, token="keep-alive", timeout=10.0)

            message_id = await RabbitMQProducer.publish_profile_push(
                serial_number=serial,
                profile_id=31337,
                profile_config=Policy(screenCaptureDisabled=True),
                profile_version=1,
                assignment_id=424242,
            )

            event = await _wait_for_sse_event(lines, kind="profile.push", timeout=10.0)
            assert f"id: {message_id}" in event
            data_line = next(line for line in event.splitlines() if line.startswith("data:"))
            payload = json.loads(data_line[len("data:") :])
            assert payload["serial_number"] == serial
            assert payload["profile_id"] == 31337
            assert payload["profile_version"] == 1
            assert payload["assignment_id"] == 424242
            assert payload["profile_config"]["screenCaptureDisabled"] is True
        finally:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)

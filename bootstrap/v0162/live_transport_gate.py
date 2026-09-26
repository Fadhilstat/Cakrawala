[Reading 473 lines from start (total: 473 lines, 0 remaining)]

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import BinaryIO, Any

from .evidence import canonical_json_bytes
from .demo_command_queue import (
    DemoCommandQueueError,
    claim_demo_command,
    complete_demo_command,
    demo_command_status,
    enqueue_demo_command,
)


class TransportGateError(RuntimeError):
    pass


_HEAD_RE = re.compile(r"^[0-9a-f]{40}$")
_PICKUP_RE = re.compile(r"^mt5-\d{8}T\d{6}Z-[0-9a-f]{10}\.mt5-pickup\.zip$")
_PREFLIGHT_RE = re.compile(r"^mt5-demo-preflight-\d{8}T\d{6}Z-[0-9a-f]{12}\.json$")
_EXECUTION_RECEIPT_RE = re.compile(r"^mt5-demo-execution-\d{8}T\d{6}Z-[0-9a-f]{12}\.json$")
_MAX_HEADER_BYTES = 4096
_MAX_PICKUP_BYTES = 16 * 1024 * 1024
_MAX_PREFLIGHT_BYTES = 256 * 1024
_MAX_EXECUTION_RECEIPT_BYTES = 256 * 1024
_MAX_INBOX_CAPSULES = 100
_MAX_PREFLIGHT_EVIDENCE = 500
_MAX_EXECUTION_RECEIPTS = 500
_MAX_DEMO_JSON_BYTES = 256 * 1024


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")




def _current_source_head(source_root: Path) -> str:
    pointer = source_root / "current-head"
    if not pointer.is_file() or pointer.is_symlink():
        raise TransportGateError("current source pointer is unavailable")
    value = pointer.read_text(encoding="ascii").strip()
    if not _HEAD_RE.fullmatch(value):
        raise TransportGateError("current source pointer is invalid")
    _safe_source_path(source_root, value)
    return value

def _safe_source_path(source_root: Path, head: str) -> Path:
    if not _HEAD_RE.fullmatch(head):
        raise TransportGateError("source head must be a 40 character lowercase SHA1")
    path = source_root / f"cakrawala-{head}.zip"
    if not path.is_file():
        raise TransportGateError("requested source capsule is unavailable")
    return path


def _read_header(stdin: BinaryIO) -> dict[str, Any]:
    line = stdin.readline(_MAX_HEADER_BYTES + 1)
    if not line or len(line) > _MAX_HEADER_BYTES or not line.endswith(b"\n"):
        raise TransportGateError("upload header is missing or oversized")
    try:
        payload = json.loads(line.decode("utf-8"))
    except Exception as exc:
        raise TransportGateError("upload header is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TransportGateError("upload header must be an object")
    return payload


def _receive_upload(stdin: BinaryIO, inbox_root: Path) -> dict[str, Any]:
    header = _read_header(stdin)
    filename = str(header.get("filename") or "")
    expected_sha256 = str(header.get("sha256") or "").lower()
    try:
        size = int(header.get("size"))
    except (TypeError, ValueError) as exc:
        raise TransportGateError("upload size is invalid") from exc

    if not _PICKUP_RE.fullmatch(filename):
        raise TransportGateError("upload filename is not an MT5 pickup capsule")
    if len(expected_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha256):
        raise TransportGateError("upload SHA256 is invalid")
    if size < 1 or size > _MAX_PICKUP_BYTES:
        raise TransportGateError("upload size is outside the bounded limit")

    inbox_root.mkdir(parents=True, exist_ok=True)
    existing_capsules = list(inbox_root.glob("*.mt5-pickup.zip"))
    destination = inbox_root / filename
    if destination.exists():
        actual = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual != expected_sha256 or destination.stat().st_size != size:
            raise TransportGateError("existing pickup capsule conflicts with upload identity")
        return {
            "status": "UPLOAD_REUSED",
            "filename": filename,
            "size": size,
            "sha256": actual,
        }
    if len(existing_capsules) >= _MAX_INBOX_CAPSULES:
        raise TransportGateError("pickup inbox capacity limit reached")

    fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".partial", dir=str(inbox_root))
    digest = hashlib.sha256()
    remaining = size
    try:
        with os.fdopen(fd, "wb") as handle:
            while remaining:
                chunk = stdin.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise TransportGateError("upload ended before declared size")
                handle.write(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if stdin.read(1):
            raise TransportGateError("upload contains bytes beyond declared size")
        actual = digest.hexdigest()
        if actual != expected_sha256:
            raise TransportGateError("upload SHA256 mismatch")
        os.replace(temp_name, destination)
        sidecar = destination.with_name(destination.name + ".sha256")
        sidecar.write_text(f"{actual}  {destination.name}\n", encoding="ascii")
        return {
            "status": "UPLOAD_ACCEPTED",
            "filename": filename,
            "size": size,
            "sha256": actual,
        }
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)



def _read_json_payload(stdin: BinaryIO, *, label: str) -> dict[str, Any]:
    line = stdin.readline(_MAX_DEMO_JSON_BYTES + 1)
    if not line or len(line) > _MAX_DEMO_JSON_BYTES or not line.endswith(b"\n"):
        raise TransportGateError(f"{label} payload is missing or oversized")
    if stdin.read(1):
        raise TransportGateError(f"{label} payload contains trailing bytes")
    try:
        payload = json.loads(line.decode("utf-8"))
    except Exception as exc:
        raise TransportGateError(f"{label} payload is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TransportGateError(f"{label} payload must be an object")
    return payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_preflight_payload(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise TransportGateError("preflight upload must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise TransportGateError("preflight upload must be a JSON object")
    if payload.get("environment") != "DEMO":
        raise TransportGateError("preflight evidence must target DEMO")
    if payload.get("status") not in {"DEMO_ORDER_PREFLIGHT_PASS", "DEMO_ORDER_PREFLIGHT_REJECTED"}:
        raise TransportGateError("preflight evidence status is invalid")
    provenance = str(payload.get("instruction_provenance") or "")
    if provenance not in {"SIGNED_DEMO_INSTRUCTION", "BROKER_COMPATIBILITY_PROBE"}:
        raise TransportGateError("preflight evidence instruction provenance is invalid")
    if provenance == "BROKER_COMPATIBILITY_PROBE":
        if payload.get("strategy_signal_bound") is not False:
            raise TransportGateError("broker compatibility probe must not claim strategy signal binding")
        if payload.get("risk_permission_bound") is not False:
            raise TransportGateError("broker compatibility probe must not claim Risk Engine permission binding")
    required_flags = {
        "order_check_called": True,
        "order_send_called": False,
        "broker_mutation_performed": False,
        "execution_authorized": False,
        "live_execution_allowed": False,
        "real_demo_preflight_evidence": True,
    }
    for key, expected in required_flags.items():
        if payload.get(key) is not expected:
            raise TransportGateError(f"preflight evidence safety flag mismatch: {key}")
    instruction_id = str(payload.get("instruction_id") or "")
    account_fingerprint = str(payload.get("account_fingerprint") or "")
    for field, value in (("instruction_id", instruction_id), ("account_fingerprint", account_fingerprint)):
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise TransportGateError(f"preflight evidence {field} must be lowercase SHA256")
    return payload


def _receive_preflight_upload(stdin: BinaryIO, preflight_root: Path) -> dict[str, Any]:
    header = _read_header(stdin)
    filename = str(header.get("filename") or "")
    expected_sha256 = str(header.get("sha256") or "").lower()
    try:
        size = int(header.get("size"))
    except (TypeError, ValueError) as exc:
        raise TransportGateError("preflight upload size is invalid") from exc
    if not _PREFLIGHT_RE.fullmatch(filename):
        raise TransportGateError("upload filename is not MT5 Demo preflight evidence")
    if len(expected_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha256):
        raise TransportGateError("preflight upload SHA256 is invalid")
    if size < 1 or size > _MAX_PREFLIGHT_BYTES:
        raise TransportGateError("preflight upload size is outside the bounded limit")

    preflight_root.mkdir(parents=True, exist_ok=True)
    destination = preflight_root / filename
    existing = list(preflight_root.glob("mt5-demo-preflight-*.json"))
    if destination.exists():
        body = destination.read_bytes()
        actual = hashlib.sha256(body).hexdigest()
        _validate_preflight_payload(body)
        if actual != expected_sha256 or destination.stat().st_size != size:
            raise TransportGateError("existing preflight evidence conflicts with upload identity")
        return {"status": "PREFLIGHT_UPLOAD_REUSED", "filename": filename, "size": size, "sha256": actual}
    if len(existing) >= _MAX_PREFLIGHT_EVIDENCE:
        raise TransportGateError("preflight evidence inbox capacity limit reached")

    fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".partial", dir=str(preflight_root))
    digest = hashlib.sha256()
    remaining = size
    body = bytearray()
    try:
        with os.fdopen(fd, "wb") as handle:
            while remaining:
                chunk = stdin.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise TransportGateError("preflight upload ended before declared size")
                handle.write(chunk)
                body.extend(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if stdin.read(1):
            raise TransportGateError("preflight upload contains bytes beyond declared size")
        actual = digest.hexdigest()
        if actual != expected_sha256:
            raise TransportGateError("preflight upload SHA256 mismatch")
        _validate_preflight_payload(bytes(body))
        os.replace(temp_name, destination)
        sidecar = destination.with_name(destination.name + ".sha256")
        sidecar.write_text(f"{actual}  {destination.name}\n", encoding="ascii")
        return {"status": "PREFLIGHT_UPLOAD_ACCEPTED", "filename": filename, "size": size, "sha256": actual}
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _validate_execution_receipt_payload(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise TransportGateError("execution receipt must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise TransportGateError("execution receipt must be a JSON object")
    if payload.get("environment") != "DEMO":
        raise TransportGateError("execution receipt must target DEMO")
    if payload.get("contract") != "CAKRAWALA_MT5_SUPERVISED_DEMO_EXECUTION_V1":
        raise TransportGateError("execution receipt contract is invalid")
    allowed_statuses = {
        "DEMO_EXECUTION_BLOCKED_BY_ORDER_CHECK",
        "DEMO_EXECUTION_RECONCILED",
        "DEMO_EXECUTION_PARTIAL_RECONCILIATION_PENDING",
        "DEMO_EXECUTION_PLACED_PENDING",
        "DEMO_EXECUTION_RECONCILIATION_PENDING",
        "DEMO_EXECUTION_REJECTED",
    }
    status = str(payload.get("status") or "")
    if status not in allowed_statuses:
        raise TransportGateError("execution receipt status is invalid")
    if payload.get("live_execution_allowed") is not False:
        raise TransportGateError("execution receipt must keep live execution disabled")
    if payload.get("automatic_live_promotion") is not False:
        raise TransportGateError("execution receipt must keep automatic live promotion disabled")
    if payload.get("demo_execution_authorized") is not True:
        raise TransportGateError("execution receipt requires explicit Demo authorization")
    if payload.get("order_check_called") is not True:
        raise TransportGateError("execution receipt must include broker order_check")
    order_send_called = payload.get("order_send_called")
    if status == "DEMO_EXECUTION_BLOCKED_BY_ORDER_CHECK":
        if order_send_called is not False or payload.get("broker_mutation_performed") is not False:
            raise TransportGateError("blocked execution receipt cannot claim broker mutation")
    else:
        if order_send_called is not True:
            raise TransportGateError("execution receipt must record order_send")
    if status == "DEMO_EXECUTION_RECONCILED":
        if payload.get("broker_mutation_performed") is not True:
            raise TransportGateError("reconciled execution receipt must record broker mutation")
        if payload.get("position_reconciled") is not True:
            raise TransportGateError("reconciled execution receipt must record position reconciliation")
    if status == "DEMO_EXECUTION_REJECTED" and payload.get("broker_mutation_performed") is not False:
        raise TransportGateError("rejected execution receipt cannot claim broker mutation")
    for field in ("instruction_id", "account_fingerprint"):
        value = str(payload.get(field) or "")
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise TransportGateError(f"execution receipt {field} must be lowercase SHA256")
    receipt_id = str(payload.get("execution_receipt_id") or "")
    if status != "DEMO_EXECUTION_BLOCKED_BY_ORDER_CHECK":
        if len(receipt_id) != 64 or any(ch not in "0123456789abcdef" for ch in receipt_id):
            raise TransportGateError("execution receipt id must be lowercase SHA256")
        unsigned = dict(payload)
        unsigned.pop("execution_receipt_id", None)
        expected = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
        if receipt_id != expected:
            raise TransportGateError("execution receipt id does not match canonical payload")
    return payload


def _receive_execution_receipt_upload(stdin: BinaryIO, execution_root: Path) -> dict[str, Any]:
    header = _read_header(stdin)
    filename = str(header.get("filename") or "")
    expected_sha256 = str(header.get("sha256") or "").lower()
    try:
        size = int(header.get("size"))
    except (TypeError, ValueError) as exc:
        raise TransportGateError("execution receipt upload size is invalid") from exc
    if not _EXECUTION_RECEIPT_RE.fullmatch(filename):
        raise TransportGateError("upload filename is not MT5 Demo execution evidence")
    if len(expected_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha256):
        raise TransportGateError("execution receipt upload SHA256 is invalid")
    if size < 1 or size > _MAX_EXECUTION_RECEIPT_BYTES:
        raise TransportGateError("execution receipt upload size is outside the bounded limit")

    execution_root.mkdir(parents=True, exist_ok=True)
    destination = execution_root / filename
    existing = list(execution_root.glob("mt5-demo-execution-*.json"))
    if destination.exists():
        body = destination.read_bytes()
        actual = hashlib.sha256(body).hexdigest()
        _validate_execution_receipt_payload(body)
        if actual != expected_sha256 or destination.stat().st_size != size:
            raise TransportGateError("existing execution receipt conflicts with upload identity")
        return {"status": "EXECUTION_RECEIPT_UPLOAD_REUSED", "filename": filename, "size": size, "sha256": actual}
    if len(existing) >= _MAX_EXECUTION_RECEIPTS:
        raise TransportGateError("execution receipt inbox capacity limit reached")

    fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".partial", dir=str(execution_root))
    digest = hashlib.sha256()
    remaining = size
    body = bytearray()
    try:
        with os.fdopen(fd, "wb") as handle:
            while remaining:
                chunk = stdin.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise TransportGateError("execution receipt upload ended before declared size")
                handle.write(chunk)
                body.extend(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if stdin.read(1):
            raise TransportGateError("execution receipt upload contains bytes beyond declared size")
        actual = digest.hexdigest()
        if actual != expected_sha256:
            raise TransportGateError("execution receipt upload SHA256 mismatch")
        _validate_execution_receipt_payload(bytes(body))
        os.replace(temp_name, destination)
        sidecar = destination.with_name(destination.name + ".sha256")
        sidecar.write_text(f"{actual}  {destination.name}\n", encoding="ascii")
        return {"status": "EXECUTION_RECEIPT_UPLOAD_ACCEPTED", "filename": filename, "size": size, "sha256": actual}
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def run_transport_gate(
    command: str,
    *,
    stdin: BinaryIO,
    stdout: BinaryIO,
    source_root: str | Path,
    inbox_root: str | Path,
    preflight_root: str | Path | None = None,
    execution_root: str | Path | None = None,
    demo_queue_root: str | Path | None = None,
) -> int:
    source = Path(source_root)
    inbox = Path(inbox_root)
    preflight = Path(preflight_root) if preflight_root is not None else inbox
    execution = Path(execution_root) if execution_root is not None else inbox
    demo_queue = Path(demo_queue_root) if demo_queue_root is not None else None
    parts = command.strip().split()
    if parts == ["health"]:
        stdout.write(_json_bytes({
            "status": "CAKRAWALA_TRANSPORT_GATE_READY",
            "operations": [
                "health", "source-current", "source", "source-sha256", "upload", "upload-preflight", "upload-execution-receipt",
                *([
                    "demo-command-enqueue", "demo-command-claim", "demo-result-upload", "demo-command-status",
                ] if demo_queue is not None else []),
            ],
            "max_pickup_bytes": _MAX_PICKUP_BYTES,
            "max_demo_json_bytes": _MAX_DEMO_JSON_BYTES,
            "demo_environment_only": demo_queue is not None,
            "max_preflight_bytes": _MAX_PREFLIGHT_BYTES,
            "max_execution_receipt_bytes": _MAX_EXECUTION_RECEIPT_BYTES,
            "shell_access": False,
        }))
        return 0
    if parts == ["source-current"]:
        stdout.write((_current_source_head(source) + "\n").encode("ascii"))
        return 0
    if len(parts) == 2 and parts[0] == "source":
        capsule = _safe_source_path(source, parts[1])
        with capsule.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                stdout.write(chunk)
        return 0
    if len(parts) == 2 and parts[0] == "source-sha256":
        capsule = _safe_source_path(source, parts[1])
        digest = hashlib.sha256(capsule.read_bytes()).hexdigest()
        stdout.write((digest + "\n").encode("ascii"))
        return 0
    if parts == ["upload"]:
        stdout.write(_json_bytes(_receive_upload(stdin, inbox)))
        return 0
    if parts == ["upload-preflight"]:
        stdout.write(_json_bytes(_receive_preflight_upload(stdin, preflight)))
        return 0
    if parts == ["upload-execution-receipt"]:
        stdout.write(_json_bytes(_receive_execution_receipt_upload(stdin, execution)))
        return 0
    if demo_queue is not None and parts == ["demo-command-enqueue"]:
        payload = _read_json_payload(stdin, label="Demo command")
        try:
            receipt = enqueue_demo_command(payload, demo_queue)
        except DemoCommandQueueError as exc:
            raise TransportGateError(str(exc)) from exc
        stdout.write(_json_bytes(receipt))
        return 0
    if demo_queue is not None and len(parts) == 2 and parts[0] == "demo-command-claim":
        try:
            claimed = claim_demo_command(
                demo_queue,
                worker_id=parts[1],
                current_time_utc=_utc_now_iso(),
            )
        except DemoCommandQueueError as exc:
            raise TransportGateError(str(exc)) from exc
        stdout.write(_json_bytes(claimed))
        return 0
    if demo_queue is not None and parts == ["demo-result-upload"]:
        payload = _read_json_payload(stdin, label="Demo result")
        try:
            receipt = complete_demo_command(payload, demo_queue)
        except DemoCommandQueueError as exc:
            raise TransportGateError(str(exc)) from exc
        stdout.write(_json_bytes(receipt))
        return 0
    if demo_queue is not None and len(parts) == 2 and parts[0] == "demo-command-status":
        try:
            status = demo_command_status(demo_queue, parts[1])
        except DemoCommandQueueError as exc:
            raise TransportGateError(str(exc)) from exc
        stdout.write(_json_bytes(status))
        return 0
    raise TransportGateError("operation is not permitted")

[executed on device: vmi3564789 (23607122-f089-4b11-9ce1-b7e08bf65c90)]
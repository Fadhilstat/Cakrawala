from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEAD = "13b756e1d45423d6d675f46b618f37d58973ecf6"
RUNTIME = Path(os.environ.get("CAKRAWALA_DEMO_RUNTIME", f"/home/ops/.local/lib/cakrawala-transport/{HEAD}"))
INGRESS_ROOT = Path(os.environ.get("CAKRAWALA_MT5_INGRESS_ROOT", "/home/ops/cakrawala-mt5-ingress"))
QUEUE_ROOT = Path(os.environ.get("CAKRAWALA_DEMO_QUEUE_ROOT", "/home/ops/cakrawala-demo-queue"))
STATE_ROOT = Path(os.environ.get("CAKRAWALA_STATE_ROOT", "/home/ops/cakrawala-state"))
ENABLE_FILE = STATE_ROOT / "demo-autotrade-enabled.json"
KILL_FILE = STATE_ROOT / "demo-autotrade.kill"
STATE_FILE = STATE_ROOT / "demo-autotrade-controller.json"
RUNTIME_POLICY = STATE_ROOT / "demo-trial-policy-v0160-runtime.json"

sys.path.insert(0, str(RUNTIME))
from cakrawala.demo_command_queue import build_demo_command, enqueue_demo_command
from cakrawala.demo_trial_execution import load_demo_trial_policy
from cakrawala.evidence import atomic_write_json, canonical_json_bytes, sha256_bytes
from cakrawala.terminal import build_terminal_payload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def latest_ingress() -> Path | None:
    rows = [p for p in INGRESS_ROOT.iterdir() if p.is_dir()] if INGRESS_ROOT.is_dir() else []
    rows.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return rows[0] if rows else None


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_policy() -> dict:
    source = read_json(RUNTIME / "config" / "demo_trial_policy.json")
    source["auto_trade_scheduler_enabled"] = True
    source["operational_override"] = "OWNER_APPROVED_EXNESS_DEMO_AUTOTRADE_V1"
    source["operational_source_revision"] = HEAD
    source["real_money_enabled"] = False
    atomic_write_json(RUNTIME_POLICY, source)
    return load_demo_trial_policy(RUNTIME_POLICY)


def write_state(**fields: object) -> None:
    payload = {
        "schema_version": 1,
        "source_revision": HEAD,
        "environment": "EXNESS_DEMO",
        "real_money_enabled": False,
        "observed_at_utc": iso(utc_now()),
        **fields,
    }
    atomic_write_json(STATE_FILE, payload)
    print(json.dumps(payload, sort_keys=True))


def stable_signal_key(campaign_id: str, intent: dict) -> str:
    return sha256_bytes(canonical_json_bytes({
        "source_revision": HEAD,
        "campaign_id": campaign_id,
        "decision_passport_hash": intent.get("decision_passport_hash"),
        "instrument": intent.get("instrument"),
        "broker_symbol": intent.get("broker_symbol"),
        "side": intent.get("side"),
    }))


def main() -> int:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    QUEUE_ROOT.mkdir(parents=True, exist_ok=True)
    if KILL_FILE.exists():
        write_state(status="KILL_SWITCH_ACTIVE")
        return 0
    if not ENABLE_FILE.is_file():
        write_state(status="OWNER_ENABLE_SENTINEL_MISSING")
        return 0
    enabled = read_json(ENABLE_FILE)
    if enabled.get("source_revision") != HEAD or enabled.get("environment") != "EXNESS_DEMO":
        write_state(status="OWNER_ENABLE_SENTINEL_INVALID")
        return 0
    latest = latest_ingress()
    if latest is None:
        write_state(status="NO_MT5_INGRESS")
        return 0
    receipt_path = latest / "ingress-receipt.json"
    campaign = latest / "campaign"
    if not receipt_path.is_file() or not campaign.is_dir():
        write_state(status="LATEST_INGRESS_INCOMPLETE", ingress=str(latest))
        return 0
    receipt = read_json(receipt_path)
    campaign_id = latest.name
    prior = read_json(STATE_FILE) if STATE_FILE.is_file() else {}
    if prior.get("campaign_id") == campaign_id and prior.get("status") in {
        "NO_READY_DEMO_INTENT", "COMMAND_ENQUEUED", "COMMAND_REUSED", "CAMPAIGN_NOT_FRESH"
    }:
        write_state(status="NO_NEW_CAMPAIGN", campaign_id=campaign_id, previous_status=prior.get("status"))
        return 0
    os.chdir(RUNTIME)
    policy = runtime_policy()
    payload = build_terminal_payload(
        campaign,
        source_revision=HEAD,
        demo_trial_policy_path=RUNTIME_POLICY,
    )
    freshness = payload.get("campaign", {}).get("data_freshness")
    if freshness != "FRESH":
        write_state(status="CAMPAIGN_NOT_FRESH", campaign_id=campaign_id, data_freshness=freshness)
        return 0
    demo_state = payload.get("demo_trial_execution", {})
    if demo_state.get("auto_trade_scheduler_enabled") is not True or demo_state.get("real_money_enabled") is not False:
        write_state(status="DEMO_AUTOTRADE_POLICY_BLOCKED", campaign_id=campaign_id)
        return 0
    intents = payload.get("demo_trial_execution_intents") or []
    ready = [item for item in intents if item.get("state") == "READY_FOR_DEMO_ADAPTER_PREFLIGHT"]
    if not ready:
        blockers = {str(item.get("instrument")): item.get("blockers") for item in intents}
        write_state(status="NO_READY_DEMO_INTENT", campaign_id=campaign_id, blockers=blockers)
        return 0
    intent = ready[0]
    key = stable_signal_key(campaign_id, intent)
    now = utc_now()
    ttl = int(policy.get("command_ttl_seconds") or 300)
    command = build_demo_command(
        demo_intent=intent,
        operation="submit_order",
        arguments={"controller_signal_key": key, "campaign_id": campaign_id},
        issued_at_utc=iso(now),
        expires_at_utc=iso(now + timedelta(seconds=ttl)),
    )
    receipt = enqueue_demo_command(command, QUEUE_ROOT)
    status = "COMMAND_REUSED" if receipt.get("status") == "DEMO_COMMAND_REUSED" else "COMMAND_ENQUEUED"
    write_state(
        status=status,
        campaign_id=campaign_id,
        signal_key=key,
        command_id=command["command_id"],
        instrument=intent.get("instrument"),
        broker_symbol=intent.get("broker_symbol"),
        side=intent.get("side"),
        queue_status=receipt.get("status"),
        ready_intents=len(ready),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
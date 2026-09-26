from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scheduled_cycle import BASE, client

HEAD = "13b756e1d45423d6d675f46b618f37d58973ecf6"
SOURCE = BASE / "source" / HEAD
STATE = BASE / "state"
STATE_FILE = STATE / "demo-signal-heartbeat.json"
RUNTIME_POLICY = STATE / "demo-trial-policy-v0160-runtime.json"

sys.path.insert(0, str(SOURCE))
from cakrawala.demo_command_queue import build_demo_command
from cakrawala.demo_trial_execution import load_demo_trial_policy
from cakrawala.evidence import atomic_write_json
from cakrawala.terminal import build_terminal_payload


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_state(**fields: object) -> None:
    payload = {
        "schema_version": 1,
        "source_revision": HEAD,
        "environment": "EXNESS_DEMO",
        "real_money_enabled": False,
        "observed_at_utc": iso(now_utc()),
        **fields,
    }
    atomic_write_json(STATE_FILE, payload)
    print(json.dumps(payload, sort_keys=True))


def runtime_policy() -> dict:
    payload = json.loads((SOURCE / "config" / "demo_trial_policy.json").read_text(encoding="utf-8"))
    payload["auto_trade_scheduler_enabled"] = True
    payload["operational_override"] = "OWNER_APPROVED_EXNESS_DEMO_AUTOTRADE_V1"
    payload["operational_source_revision"] = HEAD
    payload["real_money_enabled"] = False
    atomic_write_json(RUNTIME_POLICY, payload)
    return load_demo_trial_policy(RUNTIME_POLICY)


def enqueue(command: dict) -> dict:
    ssh = client()
    stdin, stdout, stderr = ssh.exec_command("demo-command-enqueue", timeout=20)
    stdin.write((json.dumps(command, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    stdin.channel.shutdown_write()
    body = stdout.read().decode("utf-8", errors="replace").strip()
    error = stderr.read().decode("utf-8", errors="replace").strip()
    rc = stdout.channel.recv_exit_status()
    ssh.close()
    if rc != 0:
        raise RuntimeError(error or f"Demo enqueue failed with exit {rc}")
    return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and enqueue one exact-source EXNESS_DEMO command from a fresh local campaign")
    parser.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    if not SOURCE.is_dir() or not args.campaign.is_dir():
        write_state(status="SOURCE_OR_CAMPAIGN_MISSING")
        return 0
    prior = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.is_file() else {}
    campaign_id = args.campaign.name
    if prior.get("campaign_id") == campaign_id and prior.get("status") in {"COMMAND_ENQUEUED", "NO_READY_DEMO_INTENT"}:
        write_state(status="CAMPAIGN_ALREADY_PROCESSED", campaign_id=campaign_id)
        return 0
    os.chdir(SOURCE)
    policy = runtime_policy()
    payload = build_terminal_payload(args.campaign, source_revision=HEAD, demo_trial_policy_path=RUNTIME_POLICY)
    freshness = payload.get("campaign", {}).get("data_freshness")
    if freshness != "FRESH":
        write_state(status="CAMPAIGN_NOT_FRESH", campaign_id=campaign_id, data_freshness=freshness)
        return 0
    demo_state = payload.get("demo_trial_execution", {})
    if demo_state.get("auto_trade_scheduler_enabled") is not True or demo_state.get("real_money_enabled") is not False:
        write_state(status="AUTOTRADE_POLICY_BLOCKED", campaign_id=campaign_id)
        return 0
    intents = payload.get("demo_trial_execution_intents") or []
    ready = [item for item in intents if item.get("state") == "READY_FOR_DEMO_ADAPTER_PREFLIGHT"]
    if not ready:
        blockers = {str(item.get("instrument")): item.get("blockers") for item in intents}
        write_state(status="NO_READY_DEMO_INTENT", campaign_id=campaign_id, blockers=blockers)
        return 0
    intent = ready[0]
    issued = now_utc()
    command = build_demo_command(
        demo_intent=intent,
        operation="submit_order",
        arguments={"campaign_id": campaign_id},
        issued_at_utc=iso(issued),
        expires_at_utc=iso(issued + timedelta(seconds=int(policy.get("command_ttl_seconds") or 300))),
    )
    receipt = enqueue(command)
    write_state(
        status="COMMAND_ENQUEUED" if receipt.get("status") == "DEMO_COMMAND_ENQUEUED" else str(receipt.get("status")),
        campaign_id=campaign_id,
        command_id=command["command_id"],
        instrument=intent.get("instrument"),
        broker_symbol=intent.get("broker_symbol"),
        side=intent.get("side"),
        ready_intents=len(ready),
        queue_status=receipt.get("status"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
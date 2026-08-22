from __future__ import annotations

import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import Flask, jsonify, request

from cakrawala.personal.forex_storage import ingest_sync_payload
from cakrawala.personal.forex_sync import parse_sync_payload

MAX_SYNC_BYTES = 2_000_000
MAX_CLOCK_SKEW = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(minutes=2)


def _bearer_token() -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return ""
    return authorization.removeprefix("Bearer ").strip()


def install_personal_forex_sync_route(server: Flask) -> None:
    @server.post("/personal/forex/sync")
    def personal_forex_sync() -> Any:
        expected_token = os.environ.get("PERSONAL_FOREX_INGEST_TOKEN", "").strip()
        database_url = os.environ.get("DATABASE_PERSONAL_URL", "").strip()
        owner_sub = os.environ.get("PERSONAL_OWNER_ID", "").strip()
        if not owner_sub:
            owner_sub = os.environ.get("PERSONAL_AUTH_USERNAME", "").strip()

        if not expected_token or not database_url or not owner_sub:
            return jsonify({"status": "unavailable"}), 503

        submitted_token = _bearer_token()
        if not submitted_token or not hmac.compare_digest(
            submitted_token,
            expected_token,
        ):
            return jsonify({"status": "unauthorized"}), 401

        content_length = request.content_length
        if content_length is not None and content_length > MAX_SYNC_BYTES:
            return jsonify({"status": "payload_too_large"}), 413
        if not request.is_json:
            return jsonify({"status": "json_required"}), 415

        raw_body = request.get_data(cache=True)
        if len(raw_body) > MAX_SYNC_BYTES:
            return jsonify({"status": "payload_too_large"}), 413
        try:
            raw_payload = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return jsonify({"status": "invalid_json"}), 400

        try:
            payload = parse_sync_payload(raw_payload)
        except ValueError as exc:
            return jsonify({"status": "invalid_payload", "detail": str(exc)}), 400

        now = datetime.now(UTC)
        if payload.captured_at < now - MAX_CLOCK_SKEW:
            return jsonify({"status": "stale_payload"}), 400
        if payload.captured_at > now + MAX_FUTURE_SKEW:
            return jsonify({"status": "future_payload"}), 400

        try:
            result = ingest_sync_payload(database_url, owner_sub, payload)
        except Exception as exc:
            return jsonify(
                {
                    "status": "storage_error",
                    "error_type": type(exc).__name__,
                }
            ), 503

        return jsonify(
            {
                "status": "ok",
                "duplicate_batch": result.duplicate_batch,
                "inserted_positions": result.inserted_positions,
                "inserted_deals": result.inserted_deals,
                "payload_hash": payload.payload_hash,
            }
        )

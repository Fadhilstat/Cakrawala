import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler


SOURCE_PLANE = "GITHUB_NATIVE"
EXECUTION_PLANE = "VERCEL_NATIVE"
CANARY_VERSION = "v1251"
SOURCE_BRANCH = "fundamental-v1251-vercel-canary"
SOURCE_BASE_SHA = "a62361e533064726bde3926060be3ca8c5b3d56a"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        source_sha = os.environ.get("VERCEL_GIT_COMMIT_SHA", "UNSET")
        seed = "|".join([
            SOURCE_PLANE,
            EXECUTION_PLANE,
            SOURCE_BRANCH,
            SOURCE_BASE_SHA,
            source_sha,
            CANARY_VERSION,
        ])
        payload = {
            "status": "PASS",
            "canary_version": CANARY_VERSION,
            "source_plane": SOURCE_PLANE,
            "execution_plane": EXECUTION_PLANE,
            "source_branch": SOURCE_BRANCH,
            "source_base_sha": SOURCE_BASE_SHA,
            "source_sha": source_sha,
            "evidence_sha256": hashlib.sha256(
                seed.encode("utf-8")
            ).hexdigest(),
            "vps_route_runtime": False,
            "rdc_required": False,
            "production_mutation": False,
            "database_mutation": False,
            "credential_copy": False,
            "failure_domains": ["github", "vercel"],
        }
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

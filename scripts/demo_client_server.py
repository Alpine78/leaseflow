from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import subprocess
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT_DIR / "demo-client"
NOTIFICATION_READ_PATH = re.compile(
    r"^/notifications/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/read$"
)
ALLOWED_ROUTES = {
    ("GET", "/health"),
    ("GET", "/properties"),
    ("POST", "/properties"),
    ("GET", "/leases"),
    ("POST", "/leases"),
    ("GET", "/lease-reminders/due-soon"),
    ("GET", "/notifications"),
}


def normalize_api_base_url(value: str) -> str:
    parsed = urlsplit(value.strip().rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("API base URL must be an https URL.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def is_allowed_proxy_request(method: str, path: str) -> bool:
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return False

    normalized_method = method.upper()
    if (normalized_method, parsed.path) in ALLOWED_ROUTES:
        return True
    return normalized_method == "PATCH" and NOTIFICATION_READ_PATH.fullmatch(parsed.path) is not None


def requires_id_token(method: str, path: str) -> bool:
    parsed = urlsplit(path)
    return not (method.upper() == "GET" and parsed.path == "/health")


def extract_tenant_id_from_jwt(token: str) -> str:
    try:
        _header, payload, _signature = token.split(".", 2)
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode())
        claims = json.loads(decoded)
    except (ValueError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("ID token is not a valid JWT.") from exc

    tenant_id = str(claims.get("custom:tenant_id", "")).strip()
    if not tenant_id:
        raise ValueError("ID token does not include custom:tenant_id.")
    return tenant_id


class DemoClientHandler(BaseHTTPRequestHandler):
    server_version = "LeaseFlowDemoClient/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send_static("index.html")
            return

        requested = self.path.lstrip("/")
        if requested in {"index.html", "styles.css", "app.js"}:
            self._send_static(requested)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/local/proxy":
                self._send_json(HTTPStatus.OK, self._proxy_api_request())
                return
            if self.path == "/local/reminder-scan":
                self._send_json(HTTPStatus.OK, self._invoke_reminder_scan())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send_static(self, filename: str) -> None:
        path = STATIC_DIR / filename
        if not path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Static file not found"})
            return

        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(path.suffix, "application/octet-stream")
        body = path.read_bytes()
        self.send_response(int(HTTPStatus.OK))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy_api_request(self) -> dict[str, Any]:
        payload = self._read_json()
        method = str(payload.get("method", "")).upper()
        path = str(payload.get("path", ""))
        token = str(payload.get("token", "")).strip()
        body = payload.get("body")

        if not is_allowed_proxy_request(method, path):
            raise ValueError("Requested API route is not allowed by the demo proxy.")
        if requires_id_token(method, path) and not token:
            raise ValueError("ID token is required for protected demo routes.")

        api_base_url = normalize_api_base_url(str(payload.get("apiBaseUrl", "")))
        url = f"{api_base_url}{path}"
        request_body = None
        headers = {"Accept": "application/json"}
        if body is not None:
            request_body = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = Request(url, data=request_body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read().decode()
                status_code = response.status
        except HTTPError as exc:
            response_body = exc.read().decode()
            status_code = exc.code
        except URLError as exc:
            return {"statusCode": 502, "body": {"error": f"API request failed: {exc.reason}"}}

        return {"statusCode": status_code, "body": _parse_json_or_text(response_body)}

    def _invoke_reminder_scan(self) -> dict[str, Any]:
        payload = self._read_json()
        token = str(payload.get("token", "")).strip()
        region = str(payload.get("region", "eu-north-1")).strip() or "eu-north-1"
        function_name = str(payload.get("functionName", "leaseflow-dev-backend")).strip()
        days = int(payload.get("days", 7))
        as_of_date = str(payload.get("asOfDate", "")).strip()
        tenant_id = extract_tenant_id_from_jwt(token)

        detail: dict[str, Any] = {"tenant_id": tenant_id, "days": days}
        if as_of_date:
            detail["as_of_date"] = as_of_date
        lambda_payload = {
            "source": "leaseflow.internal",
            "detail-type": "scan_due_lease_reminders",
            "detail": detail,
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as response_file:
            response_path = Path(response_file.name)

        try:
            result = subprocess.run(
                [
                    "aws",
                    "lambda",
                    "invoke",
                    "--region",
                    region,
                    "--function-name",
                    function_name,
                    "--cli-binary-format",
                    "raw-in-base64-out",
                    "--payload",
                    json.dumps(lambda_payload),
                    str(response_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return {"statusCode": 502, "body": {"error": "Reminder scan invoke failed."}}

            raw_response = response_path.read_text(encoding="utf-8")
        finally:
            response_path.unlink(missing_ok=True)

        outer = _parse_json_or_text(raw_response)
        if not isinstance(outer, dict):
            return {"statusCode": 502, "body": {"error": "Unexpected Lambda response."}}

        body = _parse_json_or_text(str(outer.get("body", "{}")))
        if isinstance(body, dict):
            body.pop("tenant_id", None)
        return {"statusCode": outer.get("statusCode", 502), "body": body}

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
        encoded = json.dumps(body).encode()
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _parse_json_or_text(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LeaseFlow local demo client.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DemoClientHandler)
    print(f"LeaseFlow demo client: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LeaseFlow demo client.")


if __name__ == "__main__":
    main()

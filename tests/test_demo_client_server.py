from __future__ import annotations

import base64
import json
import unittest

from scripts.demo_client_server import (
    extract_tenant_id_from_jwt,
    is_allowed_proxy_request,
    normalize_api_base_url,
    requires_id_token,
)


def _fake_jwt(payload: dict[str, str]) -> str:
    header = {"alg": "none", "typ": "JWT"}
    parts = []
    for item in (header, payload):
        encoded = base64.urlsafe_b64encode(json.dumps(item).encode()).decode().rstrip("=")
        parts.append(encoded)
    return f"{parts[0]}.{parts[1]}.signature"


class DemoClientServerTests(unittest.TestCase):
    def test_extracts_tenant_claim_from_jwt_payload(self) -> None:
        token = _fake_jwt({"sub": "synthetic-user", "custom:tenant_id": "synthetic-tenant"})

        self.assertEqual(extract_tenant_id_from_jwt(token), "synthetic-tenant")

    def test_rejects_missing_tenant_claim(self) -> None:
        token = _fake_jwt({"sub": "synthetic-user"})

        with self.assertRaises(ValueError):
            extract_tenant_id_from_jwt(token)

    def test_allows_only_demo_api_routes(self) -> None:
        allowed = [
            ("GET", "/health"),
            ("POST", "/properties"),
            ("GET", "/properties"),
            ("POST", "/leases"),
            ("GET", "/leases"),
            ("GET", "/lease-reminders/due-soon"),
            ("GET", "/notifications"),
            ("PATCH", "/notifications/123e4567-e89b-12d3-a456-426614174000/read"),
        ]

        for method, path in allowed:
            with self.subTest(method=method, path=path):
                self.assertTrue(is_allowed_proxy_request(method, path))

    def test_rejects_non_demo_api_routes(self) -> None:
        rejected = [
            ("DELETE", "/properties/123e4567-e89b-12d3-a456-426614174000"),
            ("PATCH", "/leases/123e4567-e89b-12d3-a456-426614174000"),
            ("GET", "/admin"),
            ("POST", "/notifications"),
            ("GET", "https://example.com/health"),
        ]

        for method, path in rejected:
            with self.subTest(method=method, path=path):
                self.assertFalse(is_allowed_proxy_request(method, path))

    def test_normalizes_api_base_url(self) -> None:
        self.assertEqual(
            normalize_api_base_url(" https://api.example.invalid/dev/ "),
            "https://api.example.invalid/dev",
        )

    def test_requires_token_for_protected_routes_only(self) -> None:
        self.assertFalse(requires_id_token("GET", "/health"))
        self.assertTrue(requires_id_token("GET", "/properties"))
        self.assertTrue(requires_id_token("POST", "/properties"))


if __name__ == "__main__":
    unittest.main()

import pytest

from app.auth import AuthError, extract_auth_context


def test_extract_auth_context_success() -> None:
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            }
        }
    }
    auth = extract_auth_context(event)
    assert auth.user_id == "user-123"
    assert auth.tenant_id == "tenant-123"


def test_extract_auth_context_missing_claims() -> None:
    with pytest.raises(AuthError):
        extract_auth_context({"requestContext": {}})

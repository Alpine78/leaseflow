import pytest

from app.auth import AuthError, extract_auth_context


def _event_with_claims(claims: dict[str, str]) -> dict:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": claims,
                }
            }
        }
    }


def test_extract_auth_context_success() -> None:
    event = _event_with_claims(
        {
            "sub": "user-123",
            "custom:tenant_id": "tenant-123",
        }
    )
    auth = extract_auth_context(event)
    assert auth.user_id == "user-123"
    assert auth.tenant_id == "tenant-123"


def test_extract_auth_context_missing_claims() -> None:
    with pytest.raises(AuthError):
        extract_auth_context({"requestContext": {}})


@pytest.mark.parametrize(
    "claims",
    [
        {"custom:tenant_id": "tenant-123"},
        {"sub": "user-123"},
    ],
)
def test_extract_auth_context_rejects_missing_required_claim(claims: dict[str, str]) -> None:
    with pytest.raises(AuthError, match="JWT must include 'sub' and 'custom:tenant_id' claims."):
        extract_auth_context(_event_with_claims(claims))


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "   ", "custom:tenant_id": "tenant-123"},
        {"sub": "user-123", "custom:tenant_id": "   "},
    ],
)
def test_extract_auth_context_rejects_blank_required_claim(claims: dict[str, str]) -> None:
    with pytest.raises(AuthError, match="JWT must include 'sub' and 'custom:tenant_id' claims."):
        extract_auth_context(_event_with_claims(claims))

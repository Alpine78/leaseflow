from __future__ import annotations

from app.models import AuthContext


class AuthError(ValueError):
    """Raised when request authentication context is invalid."""


def extract_auth_context(event: dict) -> AuthContext:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    if not claims:
        raise AuthError("Missing JWT claims.")

    user_id = claims.get("sub")
    tenant_id = claims.get("custom:tenant_id")
    if not user_id or not tenant_id:
        raise AuthError("JWT must include 'sub' and 'custom:tenant_id' claims.")

    return AuthContext(user_id=str(user_id), tenant_id=str(tenant_id))

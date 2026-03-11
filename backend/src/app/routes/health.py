from __future__ import annotations

from typing import Any


def get_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "leaseflow-backend",
    }

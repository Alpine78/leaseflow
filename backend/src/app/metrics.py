from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping


def build_emf_payload(
    *,
    namespace: str,
    environment: str,
    service: str,
    operation: str,
    result: str,
    metrics: Mapping[str, int | float],
    timestamp_ms: int | None = None,
) -> dict[str, object]:
    if any(not isinstance(value, int | float) for value in metrics.values()):
        raise TypeError("EMF metric values must be numeric.")

    dimensions = ["environment", "service", "operation", "result"]
    return {
        "_aws": {
            "Timestamp": timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": namespace,
                    "Dimensions": [dimensions],
                    "Metrics": [{"Name": name, "Unit": "Count"} for name in metrics],
                }
            ],
        },
        "environment": environment,
        "service": service,
        "operation": operation,
        "result": result,
        **dict(metrics),
    }


def emit_emf_metrics(
    *,
    namespace: str,
    environment: str,
    service: str,
    operation: str,
    result: str,
    metrics: Mapping[str, int | float],
    writer: Callable[[str], object] = print,
) -> None:
    writer(
        json.dumps(
            build_emf_payload(
                namespace=namespace,
                environment=environment,
                service=service,
                operation=operation,
                result=result,
                metrics=metrics,
            ),
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )

from __future__ import annotations

import json

from app.metrics import build_emf_payload


def test_build_emf_payload_uses_safe_dimensions_and_count_metrics() -> None:
    payload = build_emf_payload(
        namespace="LeaseFlow/NotificationEmailDelivery",
        environment="test",
        service="backend",
        operation="deliver_notification_emails",
        result="completed",
        metrics={
            "candidate_count": 2,
            "created_delivery_count": 1,
            "attempted_count": 1,
        },
        timestamp_ms=1_779_000_000_000,
    )

    assert payload == {
        "_aws": {
            "Timestamp": 1_779_000_000_000,
            "CloudWatchMetrics": [
                {
                    "Namespace": "LeaseFlow/NotificationEmailDelivery",
                    "Dimensions": [["environment", "service", "operation", "result"]],
                    "Metrics": [
                        {"Name": "candidate_count", "Unit": "Count"},
                        {"Name": "created_delivery_count", "Unit": "Count"},
                        {"Name": "attempted_count", "Unit": "Count"},
                    ],
                }
            ],
        },
        "environment": "test",
        "service": "backend",
        "operation": "deliver_notification_emails",
        "result": "completed",
        "candidate_count": 2,
        "created_delivery_count": 1,
        "attempted_count": 1,
    }
    assert "tenant" not in json.dumps(payload).lower()
    assert "recipient" not in json.dumps(payload).lower()


def test_build_emf_payload_rejects_non_numeric_metric_values() -> None:
    try:
        build_emf_payload(
            namespace="LeaseFlow/NotificationEmailDelivery",
            environment="test",
            service="backend",
            operation="deliver_notification_emails",
            result="completed",
            metrics={"candidate_count": "1"},
            timestamp_ms=1_779_000_000_000,
        )
    except TypeError as exc:
        assert str(exc) == "EMF metric values must be numeric."
    else:
        raise AssertionError("Expected TypeError for non-numeric EMF metric value.")

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest


def _feedback_module():
    return importlib.import_module("app.routes.ses_provider_feedback")


class _FakeDb:
    def __init__(self, *, processed: bool = True) -> None:
        self.processed = processed
        self.calls: list[tuple[UUID, str]] = []

    def process_ses_provider_feedback(
        self,
        *,
        event_correlation_token: UUID,
        feedback_type: str,
    ) -> SimpleNamespace:
        self.calls.append((event_correlation_token, feedback_type))
        if not self.processed:
            return SimpleNamespace(
                processed=False,
                feedback_type=feedback_type,
                bounce_count=0,
                complaint_count=0,
                suppressed_contact_count=0,
                unknown_correlation_count=1,
            )
        return SimpleNamespace(
            processed=True,
            feedback_type=feedback_type,
            bounce_count=1 if feedback_type == "bounce" else 0,
            complaint_count=1 if feedback_type == "complaint" else 0,
            suppressed_contact_count=1,
            unknown_correlation_count=0,
        )


def _event(detail_type: str = "Email Bounced", token: object | None = None) -> dict[str, Any]:
    if token is None:
        token = "11111111-1111-4111-8111-111111111111"
    return {
        "version": "0",
        "id": "event-id-that-must-not-be-a-metric-dimension",
        "source": "aws.ses",
        "detail-type": detail_type,
        "detail": {
            "mail": {
                "destination": ["recipient@example.test"],
                "tags": {
                    "leaseflow_delivery_correlation": [token],
                    "raw_provider_tag": ["not-used"],
                },
            },
            "bounce": {
                "bounceType": "Permanent",
                "bouncedRecipients": [{"emailAddress": "recipient@example.test"}],
            },
            "complaint": {
                "complainedRecipients": [{"emailAddress": "recipient@example.test"}],
            },
        },
    }


def _capture_metrics(monkeypatch) -> list[dict[str, Any]]:
    feedback = _feedback_module()
    emitted: list[dict[str, Any]] = []

    def _emit(**kwargs: Any) -> None:
        emitted.append(kwargs)

    monkeypatch.setattr(feedback, "emit_emf_metrics", _emit, raising=False)
    return emitted


def test_processes_bounce_event_by_correlation_token(monkeypatch) -> None:
    feedback = _feedback_module()
    db = _FakeDb()
    emitted = _capture_metrics(monkeypatch)

    payload = feedback.process_ses_provider_feedback(
        _event("Email Bounced"),
        db,
        SimpleNamespace(app_env="test"),
    )

    token = UUID("11111111-1111-4111-8111-111111111111")
    assert db.calls == [(token, "bounce")]
    assert payload == {
        "processed": True,
        "feedback_type": "bounce",
        "bounce_count": 1,
        "complaint_count": 0,
        "suppressed_contact_count": 1,
        "unknown_correlation_count": 0,
    }
    assert emitted == [
        {
            "namespace": "LeaseFlow/NotificationEmailDelivery",
            "environment": "test",
            "service": "backend",
            "operation": "process_ses_provider_feedback",
            "result": "processed",
            "metrics": {
                "bounce_count": 1,
                "complaint_count": 0,
                "suppressed_contact_count": 1,
            },
        }
    ]


def test_processes_complaint_event_by_correlation_token(monkeypatch) -> None:
    feedback = _feedback_module()
    db = _FakeDb()
    _capture_metrics(monkeypatch)

    payload = feedback.process_ses_provider_feedback(
        _event("Email Complaint Received"),
        db,
        SimpleNamespace(app_env="test"),
    )

    assert db.calls == [(UUID("11111111-1111-4111-8111-111111111111"), "complaint")]
    assert payload["feedback_type"] == "complaint"
    assert payload["bounce_count"] == 0
    assert payload["complaint_count"] == 1
    assert payload["suppressed_contact_count"] == 1


def test_unknown_correlation_token_is_safe_noop(monkeypatch) -> None:
    feedback = _feedback_module()
    db = _FakeDb(processed=False)
    emitted = _capture_metrics(monkeypatch)

    payload = feedback.process_ses_provider_feedback(
        _event("Email Bounced"),
        db,
        SimpleNamespace(app_env="test"),
    )

    assert payload == {
        "processed": False,
        "feedback_type": "bounce",
        "bounce_count": 0,
        "complaint_count": 0,
        "suppressed_contact_count": 0,
        "unknown_correlation_count": 1,
    }
    assert emitted[0]["result"] == "unknown"


def test_rejects_missing_correlation_token_without_leaking_raw_payload(monkeypatch) -> None:
    feedback = _feedback_module()
    event = _event("Email Bounced")
    event["detail"]["mail"]["tags"] = {}
    _capture_metrics(monkeypatch)

    with pytest.raises(ValueError, match="SES event is missing delivery correlation token."):
        feedback.process_ses_provider_feedback(event, _FakeDb(), SimpleNamespace(app_env="test"))


def test_rejects_malformed_correlation_token_without_leaking_raw_payload(monkeypatch) -> None:
    feedback = _feedback_module()
    _capture_metrics(monkeypatch)

    with pytest.raises(ValueError, match="SES delivery correlation token is invalid."):
        feedback.process_ses_provider_feedback(
            _event("Email Bounced", token="not-a-uuid"),
            _FakeDb(),
            SimpleNamespace(app_env="test"),
        )


def test_metrics_do_not_include_sensitive_payload_values(monkeypatch) -> None:
    feedback = _feedback_module()
    emitted = _capture_metrics(monkeypatch)

    feedback.process_ses_provider_feedback(
        _event("Email Bounced"),
        _FakeDb(),
        SimpleNamespace(app_env="test"),
    )

    emitted_text = str(emitted)
    assert "recipient@example.test" not in emitted_text
    assert "11111111-1111-4111-8111-111111111111" not in emitted_text
    assert "event-id-that-must-not-be-a-metric-dimension" not in emitted_text
    assert "raw_provider_tag" not in emitted_text
    assert "tenant" not in emitted_text.lower()
    assert "contact_id" not in emitted_text
    assert "notification_id" not in emitted_text

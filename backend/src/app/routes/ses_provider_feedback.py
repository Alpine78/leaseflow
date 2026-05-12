from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import Settings
from app.db import Database
from app.metrics import emit_emf_metrics

_METRIC_NAMESPACE = "LeaseFlow/NotificationEmailDelivery"
_METRIC_SERVICE = "backend"
_METRIC_OPERATION = "process_ses_provider_feedback"
_CORRELATION_TAG = "leaseflow_delivery_correlation"
_FEEDBACK_TYPES = {
    "Email Bounced": "bounce",
    "Email Complaint Received": "complaint",
}


def process_ses_provider_feedback(
    event: dict[str, Any],
    db: Database,
    settings: Settings,
) -> dict[str, Any]:
    feedback_type = _FEEDBACK_TYPES.get(str(event.get("detail-type", "")))
    if feedback_type is None:
        payload = _payload(
            processed=False,
            feedback_type="ignored",
            bounce_count=0,
            complaint_count=0,
            suppressed_contact_count=0,
            unknown_correlation_count=0,
        )
        _emit_feedback_metrics(settings=settings, result="ignored", payload=payload)
        return payload

    correlation_token = _parse_correlation_token(event)
    result = db.process_ses_provider_feedback(
        event_correlation_token=correlation_token,
        feedback_type=feedback_type,
    )
    payload = _payload(
        processed=result.processed,
        feedback_type=result.feedback_type,
        bounce_count=result.bounce_count,
        complaint_count=result.complaint_count,
        suppressed_contact_count=result.suppressed_contact_count,
        unknown_correlation_count=result.unknown_correlation_count,
    )
    _emit_feedback_metrics(
        settings=settings,
        result="unknown" if result.unknown_correlation_count else "processed",
        payload=payload,
    )
    return payload


def _parse_correlation_token(event: dict[str, Any]) -> UUID:
    tags = ((event.get("detail") or {}).get("mail") or {}).get("tags") or {}
    raw_token = tags.get(_CORRELATION_TAG)
    if isinstance(raw_token, list):
        raw_token = raw_token[0] if raw_token else None
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise ValueError("SES event is missing delivery correlation token.")

    try:
        return UUID(raw_token.strip())
    except ValueError as exc:
        raise ValueError("SES delivery correlation token is invalid.") from exc


def _payload(
    *,
    processed: bool,
    feedback_type: str,
    bounce_count: int,
    complaint_count: int,
    suppressed_contact_count: int,
    unknown_correlation_count: int,
) -> dict[str, Any]:
    return {
        "processed": processed,
        "feedback_type": feedback_type,
        "bounce_count": bounce_count,
        "complaint_count": complaint_count,
        "suppressed_contact_count": suppressed_contact_count,
        "unknown_correlation_count": unknown_correlation_count,
    }


def _emit_feedback_metrics(
    *,
    settings: Settings,
    result: str,
    payload: dict[str, Any],
) -> None:
    emit_emf_metrics(
        namespace=_METRIC_NAMESPACE,
        environment=settings.app_env,
        service=_METRIC_SERVICE,
        operation=_METRIC_OPERATION,
        result=result,
        metrics={
            "bounce_count": payload["bounce_count"],
            "complaint_count": payload["complaint_count"],
            "suppressed_contact_count": payload["suppressed_contact_count"],
        },
    )

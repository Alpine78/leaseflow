from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(slots=True)
class AuthContext:
    user_id: str
    tenant_id: str


@dataclass(slots=True)
class PropertyCreate:
    name: str
    address: str


@dataclass(slots=True)
class Property:
    property_id: UUID
    tenant_id: str
    name: str
    address: str
    created_at: datetime


@dataclass(slots=True)
class Lease:
    lease_id: UUID
    tenant_id: str
    property_id: UUID
    resident_name: str
    rent_due_day_of_month: int | None
    start_date: date
    end_date: date
    created_at: datetime


@dataclass(slots=True)
class LeaseReminderCandidate:
    lease_id: UUID
    tenant_id: str
    property_id: UUID
    resident_name: str
    rent_due_day_of_month: int
    due_date: date
    days_until_due: int


@dataclass(slots=True)
class Notification:
    notification_id: UUID
    tenant_id: str
    lease_id: UUID
    type: str
    title: str
    message: str
    due_date: date
    created_at: datetime
    read_at: datetime | None


@dataclass(slots=True)
class NotificationContact:
    contact_id: UUID
    tenant_id: str
    email: str
    enabled: bool
    created_at: datetime


@dataclass(slots=True)
class NotificationEmailDelivery:
    delivery_id: UUID
    tenant_id: str
    notification_id: UUID
    contact_id: UUID
    recipient_email: str
    subject: str
    body: str
    due_date: date
    status: str
    attempt_count: int
    last_attempt_at: datetime | None
    sent_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class NotificationEmailDeliveryPreparationResult:
    tenant_id: str | None
    candidate_count: int
    created_count: int
    duplicate_count: int


@dataclass(slots=True)
class ReminderScanResult:
    tenant_id: str | None
    as_of_date: date
    days: int
    tenant_count: int
    candidate_count: int
    created_count: int
    duplicate_count: int

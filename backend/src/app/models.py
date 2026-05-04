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
class ReminderScanResult:
    tenant_id: str | None
    as_of_date: date
    days: int
    tenant_count: int
    candidate_count: int
    created_count: int
    duplicate_count: int

from dataclasses import dataclass
from datetime import datetime
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

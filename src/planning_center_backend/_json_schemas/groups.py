from __future__ import annotations

from datetime import datetime
from typing import Optional

import msgspec


class _ApiBase(msgspec.Struct):
    data: dict
    included: list
    meta: dict
    links: Optional[dict] = None


class GroupSchema(_ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups/<id>
    data: GroupData


class GroupsSchema(_ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups
    data: list[GroupData]


class _ObjectData(msgspec.Struct, forbid_unknown_fields=True):
    type: str
    id: str
    attributes: dict
    relationships: dict
    links: dict


class GroupData(_ObjectData):
    attributes: GroupAttributes


class GroupAttributes(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    description: Optional[str]
    schedule: Optional[str]
    contact_email: Optional[str]
    memberships_count: int
    created_at: datetime
    enrollment_open: bool
    enrollment_strategy: str
    events_visibility: str
    location_type_preference: str
    public_church_center_web_url: Optional[str]
    header_image: dict
    archived_at: Optional[datetime] = None
    virtual_location_url: Optional[str] = None


class MembershipsSchema(_ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups/<id>/memberships
    data: list[MembershipData]


class MembershipData(_ObjectData):
    attributes: MembershipAttributes


class MembershipAttributes(msgspec.Struct, forbid_unknown_fields=True):
    account_center_identifier: int
    first_name: str
    last_name: str
    role: str
    email_address: str
    phone_number: str
    joined_at: datetime
    color_identifier: int
    avatar_url: str


class EventsSchema(_ApiBase):
    data: list[EventData]


class EventData(_ObjectData):
    attributes: EventAttributes


class EventAttributes(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    description: str
    starts_at: datetime
    ends_at: datetime
    repeating: bool
    multi_day: bool
    attendance_requests_enabled: bool
    automated_reminder_enabled: bool
    reminders_sent: bool
    reminders_sent_at: Optional[datetime]
    canceled: bool
    canceled_at: Optional[datetime]
    location_type_preference: str
    virtual_location_url: Optional[str]
    visitors_count: Optional[int]


class TagsSchema(_ApiBase):
    data: list[TagData]


class TagData(_ObjectData):
    attributes: TagAttributes


class TagAttributes(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    position: int

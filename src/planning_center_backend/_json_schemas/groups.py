from __future__ import annotations

from datetime import datetime
from typing import Optional

import msgspec

from .base import ApiBase, _DataBase
from ..maps import LatLong


# region Groups

class GroupSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups/<id>
    data: GroupData


class GroupsSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups
    data: list[GroupData]


class GroupData(_DataBase):
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


# endregion

# region Membership

class MembershipsSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups/<id>/memberships
    data: list[MembershipData]


class MembershipData(_DataBase):
    attributes: MembershipAttributes


class MembershipAttributes(msgspec.Struct, forbid_unknown_fields=True):
    first_name: str
    last_name: str
    role: str
    phone_number: str
    email_address: str
    account_center_identifier: int
    joined_at: datetime
    color_identifier: int
    avatar_url: str


# endregion

# region Events

class EventsSchema(ApiBase):
    data: list[EventData]


class EventData(_DataBase):
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


# endregion

# region Tags
class TagsSchema(ApiBase):
    data: list[TagData]


class TagSchema(ApiBase):
    data: TagData


class TagData(_DataBase):
    attributes: TagAttributes


class TagAttributes(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    position: int

# endregion

# region People


class PeopleSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/groups/v2/groups/<id>/memberships
    data: list[PersonData]


class PersonData(_DataBase):
    attributes: PersonAttributes


class PersonAttributes(msgspec.Struct, forbid_unknown_fields=True):
    first_name: str
    last_name: str
    addresses: list
    avatar_url: str
    created_at: datetime
    email_addresses: list
    permissions: str
    phone_numbers: list


# endregion

# region Locations

class LocationsSchema(ApiBase):
    data: list[LocationData]


class LocationData(_DataBase):
    attributes: LocationAttributes


class LocationAttributes(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    full_formatted_address: str
    latitude: str
    longitude: str
    display_preference: str
    radius: int
    strategy: str

# endregion


# region People v1

class PersonV1Data(msgspec.Struct):
    errors: list
    id: int
    account_center_id: int
    # the rest of the fields we don't care about for now

# endregion


# region Locations v1

class LocationV1Response(msgspec.Struct):
    locations: list[LocationV1Data]
    id: Optional[int] = None
    # ignore others


class LocationV1Data(msgspec.Struct):
    id: int
    name: str
    display_preference: str
    latitude: str
    longitude: str
    group_id: Optional[int]
    subpremise: Optional[str]
    full_formatted_address: str
    formatted_address: str
    approximation: LocationV1Approximation
    group_count: int
    upcoming_event_count: int
    custom: bool
    permissions: LocationV1Permissions


class LocationV1Approximation(msgspec.Struct):
    center: LatLong
    radius: int


class LocationV1Permissions(msgspec.Struct):
    can_destroy: bool
    can_share: bool
    can_update: bool

# endregion

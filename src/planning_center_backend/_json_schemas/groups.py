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


class GroupData(msgspec.Struct, forbid_unknown_fields=True):
    type: str
    id: str
    attributes: GroupAttributes
    relationships: dict
    links: dict


class GroupAttributes(msgspec.Struct, forbid_unknown_fields=True):
    contact_email: Optional[str]
    created_at: datetime
    description: Optional[str]
    enrollment_open: bool
    enrollment_strategy: str
    events_visibility: str
    header_image: dict
    location_type_preference: str
    memberships_count: int
    name: str
    public_church_center_web_url: Optional[str]
    schedule: Optional[str]
    archived_at: Optional[datetime] = None
    virtual_location_url: Optional[str] = None

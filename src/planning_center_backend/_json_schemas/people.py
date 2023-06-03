from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import msgspec

from .base import ApiBase, _DataBase


class PersonSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/people/v2/people/<id>
    data: PersonData


class PeopleSchema(ApiBase):
    # schema for https://api.planningcenteronline.com/people/v2/people
    data: list[PersonData]


class PersonData(_DataBase):
    type: str
    id: str
    attributes: PersonAttributes


class PersonAttributes(msgspec.Struct, forbid_unknown_fields=True):
    accounting_administrator: bool
    anniversary: Optional[date]
    avatar: Optional[str]
    birthdate: Optional[date]
    can_create_forms: bool
    can_email_lists: bool
    child: bool
    created_at: datetime
    demographic_avatar_url: str
    directory_status: str
    first_name: str
    gender: Optional[str]
    given_name: Optional[str]
    grade: Optional[int]
    graduation_year: Optional[int]
    inactivated_at: Optional[datetime]
    last_name: str
    first_name: Optional[str]
    medical_notes:  Optional[str]
    membership: Optional[str]
    middle_name: Optional[str]
    name: str
    nickname: Optional[str]
    passed_background_check: bool
    people_permissions: Optional[str]
    remote_id: Optional[int]
    school_type: Optional[str]
    site_administrator: bool
    status: str
    updated_at: Optional[datetime]

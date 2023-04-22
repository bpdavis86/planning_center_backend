from __future__ import annotations

from datetime import date
from enum import IntEnum, Enum
from urllib.parse import urljoin, urlparse
from typing import TYPE_CHECKING, Union, Optional, Sequence, Type, Any

import msgspec
import pandas as pd

from ._exceptions import RequestError
from ._json_schemas.groups import GroupSchema, GroupsSchema, GroupData, GroupAttributes, MembershipsSchema, \
    MembershipData, EventData, EventsSchema, TagData, TagsSchema
from . import _urls as urls

if TYPE_CHECKING:
    from .planning_center import PlanningCenterBackend


__all__ = ['GroupType', 'GroupIdentifier', 'GroupsApiProvider']


class GroupType(Enum):
    SmallGroup = 82050
    SeasonalClasses = 82051
    Online = 156530
    Unique = 'unique'


class GroupEnrollment(Enum):
    Closed = 'closed'
    RequestToJoin = 'request_to_join'
    OpenSignup = 'open_signup'


class GroupLocationType(Enum):
    Physical = 'physical'
    Virtual = 'virtual'


class GroupEventsVisibility(Enum):
    Members = 'members'
    Public = 'public'


class GroupIdentifier:
    def __init__(self, id_: int):
        self._id = id_

    def __repr__(self):
        return f'GroupIdentifier(id_={self.id_})'

    @property
    def api_url(self) -> str:
        # forward slash is necessary so last part of path is not replaced but appended
        return urljoin(urls.GROUPS_API_BASE_URL + '/', f'{self._id}')

    @property
    def frontend_url(self) -> str:
        # forward slash is necessary so last part of path is not replaced but appended
        return urljoin(urls.GROUPS_BASE_URL + '/', f'{self._id}')

    @property
    def id_(self) -> int:
        return self._id

    @classmethod
    def from_url(cls, url: str) -> GroupIdentifier:
        _parsed = urlparse(url)
        if _parsed.netloc not in (urls.API_NETLOC, urls.GROUPS_NETLOC):
            raise ValueError('URL must be based on the Planning Center Api or Groups frontend')
        _last_path = _parsed.path.split('/')[-1]
        _id = int(_last_path)
        return cls(id_=_id)

    @classmethod
    def from_id(cls, id_: int) -> GroupIdentifier:
        return cls(id_=id_)


class GroupsApiProvider:
    def __init__(self, _backend: PlanningCenterBackend):
        self._backend = _backend

    def create(self, name: str, *, group_type: GroupType = GroupType.SmallGroup) -> GroupObject:
        """
        Create a new Planning Center Small Group

        :param name: Name of new group
        :param group_type: Type of group (default Small Group)
        :return: API object for group
        """
        if not self._backend.logged_in:
            raise ValueError('User is not logged in')

        # format group creation post request
        data = {
            'group[name]': name,
            'group[group_type_id]': group_type.value
        }
        # do group creation
        r = self._backend.post(urls.GROUPS_BASE_URL, data=data, csrf_frontend_url=urls.GROUPS_ROOT_URL)

        # get the new group uri
        group_location = r.headers['Location']

        id_ = GroupIdentifier.from_url(group_location)
        return GroupObject(id_=id_, _api=self, _backend=self._backend)

    def _get_raw(self, id_: GroupIdentifier) -> GroupSchema:
        txt = self._backend.get_json(id_.api_url)
        return msgspec.json.decode(txt, type=GroupSchema)

    def _get_all_raw(self) -> Sequence[GroupData]:
        # The groups URL api returns JSON in chunks
        # For every request, if links contains 'next', that is the URL
        # of next groups chunk.
        groups = []
        url = urls.GROUPS_API_BASE_URL

        # Loop all the group chunks while we are pointed to a next URL
        while url:
            txt = self._backend.get_json(url)
            section = msgspec.json.decode(txt, type=GroupsSchema)
            groups.extend(section.data)

            if 'next' in section.links:
                url = section.links['next']
            else:
                url = None

        return groups

    def get(self, id_: Union[int, GroupIdentifier]) -> GroupObject:
        """
        Get a specific group access object by id.
        :param id_: Group id number or identifier object
        :return: Group accessor object
        """
        if isinstance(id_, int):
            id_ = GroupIdentifier.from_id(id_)
        raw = self._get_raw(id_)
        return GroupObject(id_=id_, _api=self, _backend=self._backend, _data=raw.data)

    def get_all(self) -> GroupList:
        groups_raw = self._get_all_raw()
        return GroupList([
            GroupObject(int(g.id), _api=self, _backend=self._backend, _data=g)
            for g in groups_raw
        ])


class GroupObject:
    def __init__(
            self,
            id_: Union[int, GroupIdentifier],
            _api: GroupsApiProvider,
            _backend: PlanningCenterBackend,
            _data: Optional[GroupData] = None,
    ):
        if isinstance(id_, int):
            id_ = GroupIdentifier.from_id(id_)
        self.id_ = id_
        self._api = _api
        self._backend = _backend
        self._data = None

        if _data is not None:
            self._data = _data
        # data will be lazy load

        self._deleted = False

    def refresh(self) -> None:
        """
        Refresh group attributes from server.
        :return: None
        """
        if not self._deleted:
            try:
                raw = self._api.get(self.id_)
                self._data = raw._data
            except RequestError as e:
                if e.response.status_code == 404:
                    self._deleted = True
                    return
                else:
                    raise e

    @property
    def deleted(self) -> bool:
        return self._deleted

    @property
    def frontend_url(self):
        return self.id_.frontend_url

    @property
    def api_url(self):
        return self.id_.api_url

    @property
    def settings_url(self):
        return urljoin(self.id_.frontend_url + '/', 'settings')

    @property
    def attributes(self) -> Optional[GroupAttributes]:
        if self._deleted:
            return None

        if self._data is None:
            # lazy load group data if needed
            self.refresh()
            if self._deleted:
                return None

        # if we could not load them for some reason return None
        # may want an error here instead
        if self._data is not None:
            return self._data.attributes
        else:
            return None

    def __repr__(self):
        attr = self.attributes
        if attr is None:
            return f'GroupObject(id_={self.id_.id_}, deleted={self.deleted})'
        return (
            f'GroupObject(id_={self.id_.id_}, name="{self.attributes.name}, deleted={self.deleted}")'
        )

    def delete(self) -> bool:
        """
        Delete the given group
        :return: If deletion was successful
        """
        self._backend.delete(self.frontend_url, csrf_frontend_url=self.settings_url)

        self.refresh()
        return self.deleted

    def _get_link_with_schema(self, link_name: str, schema_type: Type[msgspec.Struct]):
        if self._data is None:
            self.refresh()
        if self._data is None or link_name not in self._data.links:
            return None
        txt = self._backend.get_json(self._data.links[link_name])
        raw = msgspec.json.decode(txt, type=schema_type)
        return raw.data

    @property
    def memberships(self) -> Optional[list[MembershipData]]:
        return self._get_link_with_schema('memberships', MembershipsSchema)

    @property
    def events(self) -> Optional[list[EventData]]:
        return self._get_link_with_schema('events', EventsSchema)

    @property
    def tags(self) -> Optional[list[TagData]]:
        return self._get_link_with_schema('tags', TagsSchema)

    def _update_setting(
            self,
            data: dict[str, Any],
            *,
            url: Optional[str] = None,
            patch: bool = False,
            put: bool = False,
            autosave: bool = False,
    ):
        _request_base = {}
        if patch:
            _request_base.update({'_method': 'patch'})
        elif put:
            _request_base.update({'_method': 'put'})
        if autosave:
            _request_base.update({'__autosave__': None})

        if url is None:
            url = self.settings_url

        self._backend.post(
            url,
            data={**data, **_request_base},
            csrf_frontend_url=self.settings_url
        )
        self.refresh()

    @property
    def name(self) -> Optional[str]:
        attr = self.attributes
        return attr.name if attr else None

    @name.setter
    def name(self, value: str):
        self._update_setting(
            {'group[name]': value},
            url=self.frontend_url,
            patch=True, autosave=True
        )

    @property
    def description(self) -> Optional[str]:
        attr = self.attributes
        return attr.description if attr else None

    @description.setter
    def description(self, value: str):
        self._update_setting({'group[description]': value}, put=True, autosave=True)

    @property
    def group_type(self) -> Optional[GroupType]:
        if self._data is None:
            self.refresh()
        if self._data is None:
            return None
        # improve robustness
        id_ = int(self._data.relationships['group_type']['data']['id'])
        try:
            return GroupType(id_)
        except ValueError:
            return GroupType.Unique

    @group_type.setter
    def group_type(self, value: GroupType):
        self._update_setting(
            {'group[group_type_id]': value.value},
            url=self.frontend_url,
            patch=True, autosave=True
        )

    @property
    def schedule(self) -> Optional[str]:
        attr = self.attributes
        return attr.schedule if attr else None

    @schedule.setter
    def schedule(self, value: str):
        self._update_setting({'group[schedule]': value}, put=True, autosave=True)

    def set_publicly_display_meeting_schedule(self, value: bool):
        # this is not in the API for some reason
        self._update_setting(
            {'group[publicly_display_meeting_schedule]': int(value)},
            put=True, autosave=True
        )

    @property
    def publicly_visible(self) -> Optional[bool]:
        attr = self.attributes
        return attr.public_church_center_web_url is not None if attr else None

    @publicly_visible.setter
    def publicly_visible(self, value: bool):
        self._update_setting(
            {'group[publicly_visible]': 'true' if value else 'false'},
            put=True, autosave=True
        )

    @property
    def public_church_center_web_url(self) -> Optional[str]:
        attr = self.attributes
        return attr.public_church_center_web_url if attr else None

    @property
    def enrollment_strategy(self) -> Optional[GroupEnrollment]:
        attr = self.attributes
        return GroupEnrollment(attr.enrollment_strategy) if attr else None

    @enrollment_strategy.setter
    def enrollment_strategy(self, value: GroupEnrollment):
        self._update_setting({'group[public_enrollment]': value.value}, put=True, autosave=True)

    @property
    def contact_email(self) -> Optional[str]:
        attr = self.attributes
        return attr.contact_email if attr else None

    @contact_email.setter
    def contact_email(self, value: Optional[str]):
        self._update_setting(
            {'group[contact_email]': '' if value is None else value},
            patch=True, autosave=True
        )

    # TODO add tags

    def set_default_event_automated_reminders_schedule_offset(self, days: int):
        """
        Set UI option "Send reminder emails" number of days
        :param days: Number of days before event to send reminder (1-10)
        :return: None
        """
        # this is not in the API for some reason
        if days < 1 or days > 10:
            raise ValueError('Number of days must be between 1 and 10')
        seconds = days * 86400
        # this is not in the API for some reason
        self._update_setting(
            {
                'group[default_event_automated_reminders_schedule_offset]': seconds
            },
            patch=True, autosave=True
        )

    def set_default_event_automated_reminders_enabled(self, on: bool):
        """
        Set UI option "Send reminder emails"
        :param on: True or False
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {
                'group[default_event_automated_reminders_enabled]': 'true' if on else 'false',
            },
            patch=True, autosave=True
        )

    @property
    def location_type_preference(self) -> Optional[GroupLocationType]:
        attr = self.attributes
        return GroupLocationType(attr.location_type_preference) if attr else None

    @location_type_preference.setter
    def location_type_preference(self, value: GroupLocationType):
        self._update_setting({'group[location_type_preference]': value.value}, put=True, autosave=True)

    @property
    def location_id(self) -> Optional[int]:
        if self._data is None:
            self.refresh()
        if self._data is None:
            return None
        # improve robustness
        data = self._data.relationships['location']['data']
        return int(data['id']) if data is not None else None

    @location_id.setter
    def location_id(self, value: Optional[int]):
        self._update_setting(
            {'group[location_id]': value if value is not None else ''},
            patch=True, autosave=True
        )

    @property
    def virtual_location_url(self) -> Optional[str]:
        attr = self.attributes
        return attr.virtual_location_url if attr else None

    @virtual_location_url.setter
    def virtual_location_url(self, value: Optional[str]):
        self._update_setting(
            {'group[virtual_location_url]': '' if value is None else value},
            patch=True, autosave=True
        )

    @property
    def events_visibility(self) -> Optional[GroupEventsVisibility]:
        attr = self.attributes
        return GroupEventsVisibility(attr.events_visibility) if attr else None

    @events_visibility.setter
    def events_visibility(self, value: GroupEventsVisibility):
        self._update_setting({'group[events_visibility]': value.value}, put=True, autosave=True)

    def set_leader_name_visible_on_public_page(self, on: bool) -> None:
        """
        Set UI option "List leader's name publicly"
        :param on: True or False
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[leader_name_visible_on_public_page]': int(on)},
            put=True, autosave=True
        )

    def set_communication_enabled(self, on: bool):
        """
        Set UI option "Enable Group Messaging"
        :param on: True or False
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[communication_enabled]': int(on)},
            put=True, autosave=True
        )

    def set_members_can_create_forum_topics(self, on: bool):
        """
        Set UI option "Who can create new messages?"
        :param on: True or False (True corresponds to "Members and leaders" in UI)
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[members_can_create_forum_topics]': 'true' if on else 'false'},
            put=True, autosave=True
        )

    def set_enrollment_open_until(self, value: Optional[date]):
        """
        Set UI option "Auto-close enrollment on"
        :param value: Date at which enrollment closes, None for off
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[enrollment_open_until]': value.isoformat() if value else ''},
            put=True, autosave=True
        )

    def set_enrollment_limit(self, value: Optional[int]):
        """
        Set UI option "Auto-close if enrollment number reaches"
        :param value: Number at which enrollment closes, None for off
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[enrollment_limit]': value if value is not None else ''},
            put=True, autosave=True
        )

    def set_member_limit_maximum_alert(self, value: Optional[int]):
        """
        Set UI option "Create alert if group membership exceeds"
        :param value: Number at which enrollment closes, None for off
        :return: None
        """
        # this is not in the API for some reason
        self._update_setting(
            {'group[member_limit_maximum_alert]': value if value is not None else ''},
            put=True, autosave=True
        )


class GroupList(list[GroupObject]):
    def to_df(self) -> pd.DataFrame:
        """
        Get group descriptions as a pandas dataframe
        :return: Dataframe description of groups in list
        """
        groups = self
        group_attrs = [msgspec.structs.asdict(g.attributes) for g in groups]
        df = pd.DataFrame(group_attrs)
        df.insert(0, 'id', pd.Series([g.id_.id_ for g in groups]))
        df.set_index('id')
        return df


class MembersApiProvider:
    def __init__(self, _backend: PlanningCenterBackend):
        self._backend = _backend


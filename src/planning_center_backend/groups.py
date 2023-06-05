# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from enum import Enum
from urllib.parse import urljoin, urlparse
from typing import TYPE_CHECKING, Union, Optional, Type, Any

import msgspec
import pandas as pd
from bs4 import BeautifulSoup

from ._exceptions import RequestError
# from ._groups.locations import LocationsApiProvider
from ._groups.locations_v1 import LocationV1ApiProvider
from ._groups.people import GroupsPeopleApiProvider
from ._groups.tags import TagsApiProvider
from ._json_schemas.base import ApiBase
from ._json_schemas.groups import GroupSchema, GroupsSchema, GroupData, GroupAttributes, MembershipsSchema, \
    MembershipData, EventData, EventsSchema, TagData, TagsSchema, PersonV1Data
from . import _urls as urls
from .api_provider import ApiProvider

if TYPE_CHECKING:
    # avoid circular import
    from .planning_center import PlanningCenterBackend


__all__ = [
    'GroupType',
    'GroupIdentifier',
    'GroupsApiProvider',
    'GroupEnrollment',
    'GroupList',
    'GroupObject',
    'GroupEventsVisibility',
    'GroupLocationType'
]


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


class GroupsApiProvider(ApiProvider):
    def __init__(self, _backend: PlanningCenterBackend):
        super().__init__(_backend=_backend)
        self.people = GroupsPeopleApiProvider(self._backend)
        self.tags = TagsApiProvider(self._backend)
        # for now, disable the v2 API because it can return ids which are not available for this group
        # the per-group v1 api endpoint should be used instead (i.e. GroupObject.locations)
        # self.locations = LocationsApiProvider(self._backend)

    def _check_exists(self, name: str) -> bool:
        groups = self.query(name)
        for g in groups:
            if g.name == name:
                return True
        return False

    def create(self, name: str, *, group_type: GroupType = GroupType.SmallGroup) -> GroupObject:
        """
        Create a new Planning Center Small Group

        :param name: Name of new group
        :param group_type: Type of group (default Small Group)
        :return: API object for group
        """
        if not self._backend.logged_in:
            raise ValueError('User is not logged in')

        if self._check_exists(name):
            raise ValueError(f'Group with name {name} already exists')

        # format group creation post request
        data = {
            'group[name]': name,
            'group[group_type_id]': group_type.value
        }
        # do group creation
        r = self._backend.post(urls.GROUPS_BASE_URL, data=data, csrf_frontend_url=urls.GROUPS_ROOT_URL)

        if 'Location' not in r.headers:
            raise ValueError(
                'Could not get the new group ID from response, perhaps group create failed due to duplicate name'
            )
        # get the new group uri
        group_location = r.headers['Location']

        id_ = GroupIdentifier.from_url(group_location)
        return GroupObject(id_=id_, _api=self, _backend=self._backend)

    def get(self, id_: Union[int, GroupIdentifier, str]) -> GroupObject:
        """
        Get a specific group access object by id.
        :param id_: Group id number or identifier object
        :return: Group accessor object
        """
        if isinstance(id_, str):
            id_ = int(id_)
        if isinstance(id_, int):
            id_ = GroupIdentifier.from_id(id_)
        data = self.query_api(url=id_.api_url, schema=GroupSchema)
        return GroupObject(id_=id_, _api=self, _backend=self._backend, _data=data)

    def query(self, name: Optional[str] = None) -> GroupList:
        params = {}
        if name is not None:
            params['where[name]'] = name
        groups_raw = self.query_api(url=urls.GROUPS_API_BASE_URL, params=params, schema=GroupsSchema)
        return GroupList([
            # the data should not be passed down here because it's not a full data object
            GroupObject(int(g.id), _api=self, _backend=self._backend, _data=None)
            for g in groups_raw
        ])


_js_re_str = r"""(?xs)
<!\[CDATA\[ \s* 
(.*?)
(?://)? ]]>
"""

_json_re_str = r"""(?xs)
Components\.[^,\s]+, \s*
(\{.*?})\) 
, \s* document\.getElementById
"""
_json_re = re.compile(_json_re_str)


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
        self._settings_soup = None
        self.auto_refresh = True

        self.locations = LocationV1ApiProvider(_backend, self.id_.id_)

    @contextmanager
    def no_refresh(self, refresh_at_exit=True):
        """
        Context manager to temporarily disable auto-refresh.
        This is useful if one wishes to efficiently modify multiple settings at once.
        :return: Current group object
        """
        old_status = self.auto_refresh
        self.auto_refresh = False
        try:
            yield self
        finally:
            self.auto_refresh = old_status
        if refresh_at_exit:
            self.refresh()

    def _auto_refresh(self):
        if self.auto_refresh:
            self.refresh()

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
            self._refresh_settings()

    def _refresh_settings(self):
        # get settings page
        self._settings_soup = self._backend.get_frontend_soup(self.settings_url)

    def _get_settings_soup(self) -> BeautifulSoup:
        # helper for lazy load of settings page
        soup = self._settings_soup
        if soup is None:
            self._refresh_settings()
            soup = self._settings_soup
        return soup

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
    def members_url(self):
        return urljoin(self.id_.frontend_url + '/', 'members')

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

        self._auto_refresh()
        return self.deleted

    def _get_link_with_schema(self, link_name: str, schema_type: Type[ApiBase]):
        if self._data is None:
            self.refresh()
        if self._data is None or link_name not in self._data.links:
            return None
        return self._api.query_api(self._data.links[link_name], schema=schema_type)

    @property
    def memberships(self) -> Optional[list[MembershipData]]:
        return self._get_link_with_schema('memberships', MembershipsSchema)

    @property
    def events(self) -> Optional[list[EventData]]:
        return self._get_link_with_schema('events', EventsSchema)

    @property
    def tags(self) -> Optional[list[TagData]]:
        return self._get_link_with_schema('tags', TagsSchema)

    def _tag_input_to_id(self, input_: Union[str, int, TagData]) -> int:
        if isinstance(input_, TagData):
            input_ = int(input_.id)

        if isinstance(input_, str):
            found_tags = self._api.tags.query(input_)
            if len(found_tags) == 0:
                raise ValueError(f'Tag with name matching {input_} does not exist')
            if len(found_tags) > 1:
                raise ValueError(f'Multiple tags match name {input_}, please refine search')
            id_ = int(found_tags[0].id)
        elif isinstance(input_, int):
            try:
                self._api.tags.get(input_)
            except RequestError:
                raise ValueError(f'Tag with id {input_} could not be found')
            id_ = input_
        else:
            raise ValueError('input must be str (name to search), int (tag id), or TagData object')
        return id_

    def has_tag(self, input_: Union[str, int, TagData]) -> bool:
        id_ = self._tag_input_to_id(input_)
        current_tags = self.tags
        return len([t for t in current_tags if int(t.id) == id_]) > 0

    def add_tag(self, input_: Union[str, int, TagData], exists_ok: bool = True):
        id_ = self._tag_input_to_id(input_)
        # for some reason the backend will let you add a tag twice
        # this is bad, and we need to try to prevent

        # check this id is in our tags
        if self.has_tag(id_):
            if not exists_ok:
                raise ValueError('Tag already exists')
            else:
                return

        tags_url = urljoin(self.frontend_url + '/', 'tags')
        data = {'group_tag[tag_id]': id_}
        self._backend.post(tags_url, data=data, csrf_frontend_url=self.settings_url)
        self._auto_refresh()

    def delete_tag(self, input_: Union[str, int, TagData], missing_ok: bool = True):
        id_ = self._tag_input_to_id(input_)

        # check this id is in our tags
        if not self.has_tag(id_):
            if not missing_ok:
                raise ValueError('Tag does not exist in group')
            else:
                return

        # we must find the deletion URL by some frontend hackery
        tag_data = self._get_div_script_json_data(re.compile(r'tags_group_.*'))
        tags = tag_data['tags']
        this_tag = [t for t in tags if t['id'] == id_]
        if len(this_tag) == 0 or len(this_tag) > 1:
            raise RuntimeError('Error in retrieving tag metadata from frontend, check for interface changes')
        this_tag = this_tag[0]

        # finally we get the deletion url
        url = this_tag['url']
        self._backend.delete(url, csrf_frontend_url=self.settings_url)

    def _get_member_add_id(self, id_: int):
        # For some reason the member adding API uses a different ID from the standard person ID
        # We can read/create this ID by querying
        # https://groups.planningcenteronline.com/api/v1/people/<account_id>.json
        url = urljoin(urls.GROUPS_PEOPLE_V1_BASE + '/', f'{id_}.json')
        txt = self._backend.get_json(url)
        data = msgspec.json.decode(txt, type=PersonV1Data)
        if data.errors:
            raise RuntimeError(f'There were errors in the API result: {data.errors}')
        if data.account_center_id != id_:
            raise RuntimeError('Unexpected API error, ids do not match')
        return data.id

    def add_member(self, person_id: Union[str, int], leader: bool = False, notify: bool = False):
        person_id = int(person_id)
        # A different ID is used when adding member using this API
        add_person_id = self._get_member_add_id(person_id)

        data = {
            'membership[person_id]': add_person_id,
            'membership[role]': 'leader' if leader else 'member',
        }
        if notify:
            data['notify_member'] = 1
        self._backend.post(self.members_url, data=data, csrf_frontend_url=self.members_url)

    def get_member(self, person_id: Union[str, int]) -> Optional[MembershipData]:
        person_id = int(person_id)
        members = self.memberships
        this_membership = [m for m in members if int(m.attributes.account_center_identifier) == person_id]
        if len(this_membership) == 0:
            return None
        if len(this_membership) > 1:
            raise RuntimeError('More than one member matched id, should not occur')
        this_membership = this_membership[0]
        return this_membership

    def update_member(
            self,
            person_id: Union[str, int],
            leader: Optional[bool] = None,
            notify: Optional[bool] = None,
            attendance_taker: Optional[bool] = None,
    ):
        this_membership = self.get_member(person_id)
        if this_membership is None:
            raise ValueError('This person is not a member of the group')
        url = urljoin(self.frontend_url + '/', f'members/{this_membership.id}/role')

        data = {'_method': 'patch', 'utf8': '✓', 'commit': 'Update role'}
        if leader is not None:
            data['role'] = 'leader' if leader else 'member'
        if notify is not None:
            data['notify_member'] = 1 if notify else 0
        if attendance_taker is not None:
            # attendance taker must be joined with member status
            if not this_membership.attributes.role == 'leader' and 'role' not in data:
                data['role'] = 'member'
            if data['role'] == 'member':
                data['attendance_taker'] = 1 if attendance_taker else 0
        data['authenticity_token'] = self._backend.get_csrf_token(self.members_url)
        self._backend.post(url, data=data)

    def delete_member(self, person_id: Union[str, int], notify: bool = False, missing_ok: bool = False):
        person_id = int(person_id)
        this_membership = self.get_member(person_id)
        if this_membership is None:
            if missing_ok:
                return
            else:
                raise ValueError('This person is not a member of the group')

        # we have to use the same alternative addition id for deletion
        add_person_id = self._get_member_add_id(person_id)
        url = urljoin(self.frontend_url + '/', f'members/{this_membership.id}/removal')

        data = {}
        if notify is not None:
            data['notify_member'] = 1 if notify else 0
        data['authenticity_token'] = self._backend.get_csrf_token(self.members_url)
        data['membership[person_id]'] = add_person_id
        self._backend.post(url, data=data)

    # region Helpers for settings
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
        self._auto_refresh()

    def _get_ui_checkbox_status(self, name: str) -> bool:
        soup = self._get_settings_soup()
        check = soup.find(attrs={'name': name, 'class': 'checkbox'})
        if not check:
            raise RuntimeError(f'Could not find checkbox element {name}, check for UI changes')
        # check box status
        value = 'checked' in check.attrs
        return value

    def _get_ui_radio_value(self, name: str) -> str:
        soup = self._get_settings_soup()
        radios = soup.find_all(attrs={'name': name, 'class': 'radio'})
        if not radios:
            raise RuntimeError(f'Could not find radio elements with name {name}, check for UI changes')
        for r in radios:
            if 'checked' in r.attrs:
                return r.attrs['value']
        raise ValueError(f'Could not find a checked radio button with name {name}, check for UI changes')

    def _get_ui_select_value(self, name: str) -> Optional[str]:
        soup = self._get_settings_soup()
        select = soup.find(attrs={'name': name, 'class': 'select'})
        if not select:
            raise RuntimeError(f'Could not find select elements with name {name}, check for UI changes')

        selected = select.find(attrs={'selected': 'selected'})
        if not selected:
            # this is case where valueless option is selected
            return None

        return selected['value']

    def _get_settings_data_react_props(self):
        # Some of the settings have to be loaded directly from the settings frontend
        # Some of these are embedded in react class property JSON strings
        # Get the embedded React class parameters
        # This is likely to break as the frontend evolves

        soup = self._get_settings_soup()
        react_elements = soup.find_all(attrs={'data-react-class': 'AppProvider'})
        return [
            json.loads(e.attrs['data-react-props'])
            for e in react_elements
        ]

    def _get_div_script_json_data(self, div_id) -> dict:
        # Get UI info that is embedded in JS script which calls React createElement
        # Expected structure is
        # <div id=...><script>
        # //<![CDATA[
        # $(function() {
        # ...
        # Components.GroupSettings.EnrollmentSettings, (json data), document.getElementById...
        # //]]>
        # </script></div>

        # Do some regex magic to get it out
        soup = self._get_settings_soup()

        # find the div containing tags script
        div = soup.find(attrs={'id': div_id})
        if not div:
            raise RuntimeError(f'Could not script div {div_id}, check for UI changes')
        txt = div.find('script').string

        # extract JS code
        m = re.search(r'(?xs) <!\[CDATA\[ \s* (.*?) (?://)? ]]>', txt)
        if not m:
            raise RuntimeError('Could not parse JS script, check for UI changes')
        js = m.group(1)

        # extract JSON from JS code
        # m = re.search(r'(?xs) Components\.Groups\.Tags, \s* (\{.*?})\) , \s* document\.getElementById', js)
        m = re.search(_json_re, js)
        if not m:
            raise RuntimeError('Could not parse JSON from JS script, check for UI changes')
        json_txt = m.group(1)
        return json.loads(json_txt)

    # endregion

    # region Basic Group Properties

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

    @property
    def publicly_display_meeting_schedule(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        return self._get_ui_checkbox_status('group[publicly_display_meeting_schedule]')

    @publicly_display_meeting_schedule.setter
    def publicly_display_meeting_schedule(self, value: bool):
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

    def _get_react_props_for_component(self, component_name: str):
        react_data = self._get_settings_data_react_props()
        for d in react_data:
            if d['component'] == component_name:
                return d
        raise ValueError(
            f'Could not find data for component {component_name} in React data '
            'for frontend, check for UI changes'
        )

    @property
    def default_event_automated_reminders_enabled(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        data = self._get_react_props_for_component('Components.GroupSettingsEventReminderToggle')
        return data['automatedRemindersEnabled']

    @default_event_automated_reminders_enabled.setter
    def default_event_automated_reminders_enabled(self, on: bool):
        """
        Set UI option "Send reminder emails"
        :param on: True or False
        :return: None
        """
        self._update_setting(
            {'group[default_event_automated_reminders_enabled]': 'true' if on else 'false'},
            patch=True, autosave=True
        )

    @property
    def default_event_automated_reminders_schedule_offset(self) -> int:
        """
        UI option "Send reminder emails" number of days
        :return: Number of days before event to send reminder
        """
        # FRAGILE - derived from UI due to lack of API access
        data = self._get_react_props_for_component('Components.GroupSettingsEventReminderToggle')
        return data['scheduleOffset'] // 86400

    @default_event_automated_reminders_schedule_offset.setter
    def default_event_automated_reminders_schedule_offset(self, days: int):
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
        # Note - only location IDs in the v1 API seem to be valid here
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

    @property
    def leader_name_visible_on_public_page(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        return self._get_ui_checkbox_status('group[leader_name_visible_on_public_page]')

    @leader_name_visible_on_public_page.setter
    def leader_name_visible_on_public_page(self, on: bool) -> None:
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

    @property
    def communication_enabled(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        return self._get_ui_checkbox_status('group[communication_enabled]')

    @communication_enabled.setter
    def communication_enabled(self, on: bool):
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

    @property
    def members_can_create_forum_topics(self) -> bool:
        """
        UI option "Who can create new messages?"
        :return: True or False (True corresponds to "Members and leaders" in UI)
        """
        # FRAGILE - derived from UI due to lack of API access
        value = self._get_ui_radio_value('group[members_can_create_forum_topics]')
        return value == 'true'

    @members_can_create_forum_topics.setter
    def members_can_create_forum_topics(self, on: bool):
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

    @property
    def enrollment_open_until(self) -> Optional[date]:
        # FRAGILE - derived from UI due to lack of API access
        # data = self._get_react_props_for_component(
        #     'Components.GroupSettings.MembershipSettingsForm'
        # )
        # value = data['settings']['enrollmentOpenUntil']
        data = self._get_div_script_json_data(re.compile(r'enrollment_settings_group_.*'))
        value = data['enrollmentOpenUntil']

        return datetime.fromisoformat(value).date() if value is not None else None

    @enrollment_open_until.setter
    def enrollment_open_until(self, value: Optional[date]):
        """
        Set UI option "Auto-close enrollment on"
        :param value: Date at which enrollment closes, None for off
        :return: None
        """
        self._update_setting(
            {'group[enrollment_open_until]': value.isoformat() if value else ''},
            put=True, autosave=True
        )

    @property
    def enrollment_limit(self) -> Optional[int]:
        # FRAGILE - derived from UI due to lack of API access
        # data = self._get_react_props_for_component(
        #     'Components.GroupSettings.MembershipSettingsForm'
        # )
        # value = data['settings']['enrollmentLimit']
        data = self._get_div_script_json_data(re.compile(r'enrollment_settings_group_.*'))
        value = data['enrollmentLimit']
        return value

    @enrollment_limit.setter
    def enrollment_limit(self, value: Optional[int]):
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

    @property
    def member_limit_maximum_alert(self) -> Optional[int]:
        # FRAGILE - derived from UI due to lack of API access
        # data = self._get_react_props_for_component(
        #     'Components.GroupSettings.MembershipSettingsForm'
        # )
        # value = data['settings']['memberLimitMaximumAlert']
        data = self._get_div_script_json_data(re.compile(r'enrollment_settings_group_.*'))
        value = data['memberLimitMaximumAlert']
        return value

    @member_limit_maximum_alert.setter
    def member_limit_maximum_alert(self, value: Optional[int]):
        """
        Set UI option "Create alert if group membership exceeds"
        :param value: Number at which enrollment closes, None for off
        :return: None
        """
        self._update_setting(
            {'group[member_limit_maximum_alert]': value if value is not None else ''},
            put=True, autosave=True
        )

    @property
    def request_event_attendance_from_leaders(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        return self._get_ui_checkbox_status('group[request_event_attendance_from_leaders]')

    @request_event_attendance_from_leaders.setter
    def request_event_attendance_from_leaders(self, value: bool) -> None:
        self._update_setting(
            {'group[request_event_attendance_from_leaders]': int(value)},
            put=True, autosave=True
        )

    @property
    def attendance_reply_to_person_id(self) -> Optional[int]:
        # FRAGILE - derived from UI due to lack of API access
        s = self._get_ui_select_value('group[attendance_reply_to_person_id]')
        return int(s) if s is not None else None

    @attendance_reply_to_person_id.setter
    def attendance_reply_to_person_id(self, value: Optional[int]) -> None:
        self._update_setting(
            {'group[attendance_reply_to_person_id]': value if value is not None else ''},
            put=True, autosave=True
        )

    @property
    def leaders_can_search_people_database(self) -> bool:
        # FRAGILE - derived from UI due to lack of API access
        return self._get_ui_checkbox_status('group[leaders_can_search_people_database]')

    @leaders_can_search_people_database.setter
    def leaders_can_search_people_database(self, value: bool) -> None:
        self._update_setting(
            {'group[leaders_can_search_people_database]': int(value)},
            put=True, autosave=True
        )

    # endregion


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

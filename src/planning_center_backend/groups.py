from __future__ import annotations

from enum import IntEnum
from urllib.parse import urljoin, urlparse
from typing import TYPE_CHECKING, Union, Optional, Sequence

import msgspec
import pandas as pd

from ._exceptions import RequestError
from ._json_schemas.groups import GroupSchema, GroupsSchema, GroupData, GroupAttributes
from . import _urls as urls

if TYPE_CHECKING:
    from .planning_center import PlanningCenterBackend


__all__ = ['GroupType', 'GroupIdentifier', 'GroupsApiProvider']


class GroupType(IntEnum):
    SmallGroup = 82050


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

    def create(self, name: str) -> GroupObject:
        """
        Create a new Planning Center Small Group

        :param name: Name of new group
        :return: API object for group
        """
        if not self._backend.logged_in:
            raise ValueError('User is not logged in')

        # format group creation post request
        data = {
            'group[name]': name,
            'group[group_type_id]': int(GroupType.SmallGroup)
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
                else:
                    raise e

    @property
    def deleted(self) -> bool:
        return self._deleted

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
        settings_url = urljoin(self.id_.frontend_url + '/', 'settings')
        self._backend.delete(self.id_.frontend_url, csrf_frontend_url=settings_url)

        self.refresh()
        return self.deleted


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

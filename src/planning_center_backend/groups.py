from __future__ import annotations

from enum import IntEnum
from urllib.parse import urljoin, urlparse
from typing import TYPE_CHECKING

import msgspec
import pandas as pd

from ._json_schemas.groups import GroupSchema, GroupsSchema
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

    def create(self, name: str) -> GroupIdentifier:
        """
        Create a new Planning Center Small Group

        :param name: Name of new group
        :return: Identifier of new group resource
        """
        if not self._backend.logged_in:
            raise ValueError('User is not logged in')

        # get AJAX security token from frontend
        csrf_token = self._backend.get_csrf_token(urls.GROUPS_ROOT_URL)

        # format group creation post request
        data = {
            'group[name]': name,
            'group[group_type_id]': int(GroupType.SmallGroup)
        }
        # do group creation
        r = self._backend.post(urls.GROUPS_BASE_URL, data=data, csrf_token=csrf_token)

        # get the new group uri
        group_location = r.headers['Location']

        return GroupIdentifier.from_url(group_location)

    def delete(self, group: GroupIdentifier):
        """
        Delete the given group
        :param group: Identifier of group
        :return: Response object resulting from deletion
        """
        csrf_token = self._backend.get_csrf_token(
            urljoin(group.frontend_url + '/', 'settings')
        )
        self._backend.delete(group.frontend_url, csrf_token=csrf_token)

    def get(self, group: GroupIdentifier) -> msgspec.Struct:
        txt = self._backend.get_json(group.api_url)
        return msgspec.json.decode(txt, type=GroupSchema)

    def _get_all(self):
        groups = []
        url = urls.GROUPS_API_BASE_URL

        while url:
            txt = self._backend.get_json(url)
            section = msgspec.json.decode(txt, type=GroupsSchema)
            groups.extend(section.data)

            if 'next' in section.links:
                url = section.links['next']
            else:
                url = None

        return groups

    def get_all_df(self) -> pd.DataFrame:
        groups = self._get_all()
        group_attrs = [msgspec.structs.asdict(g.attributes) for g in groups]
        df = pd.DataFrame(group_attrs)
        df.insert(0, 'id', pd.Series([int(g.id) for g in groups]))
        df.set_index('id')
        return df

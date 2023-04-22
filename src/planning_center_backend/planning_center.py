from __future__ import annotations

import json
from enum import IntEnum
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests import Session, Response

_LOGIN_NEW_URL = 'https://login.planningcenteronline.com/login/new'
_LOGIN_POST_URL = 'https://login.planningcenteronline.com/login'
_LOGOUT_URL = 'https://login.planningcenteronline.com/logout'
_HOME_ROOT_URL = 'https://home.planningcenteronline.com'
_GROUPS_ROOT_URL = 'https://groups.planningcenteronline.com'
_GROUPS_BASE_URL = 'https://groups.planningcenteronline.com/groups'
_GROUPS_API_BASE_URL = 'https://api.planningcenteronline.com/groups/v2/groups'
_API_NETLOC = 'api.planningcenteronline.com'
_GROUPS_NETLOC = 'groups.planningcenteronline.com'
_TOPBAR_URL = 'https://api.planningcenteronline.com/people/v2/me/topbar'


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
        return urljoin(_GROUPS_API_BASE_URL + '/', f'{self._id}')

    @property
    def frontend_url(self) -> str:
        # forward slash is necessary so last part of path is not replaced but appended
        return urljoin(_GROUPS_BASE_URL + '/', f'{self._id}')

    @property
    def id_(self) -> int:
        return self._id

    @classmethod
    def from_url(cls, url: str) -> GroupIdentifier:
        _parsed = urlparse(url)
        if _parsed.netloc not in (_API_NETLOC, _GROUPS_NETLOC):
            raise ValueError('URL must be based on the Planning Center Api or Groups frontend')
        _last_path = _parsed.path.split('/')[-1]
        _id = int(_last_path)
        return cls(id_=_id)

    @classmethod
    def from_id(cls, id_: int) -> GroupIdentifier:
        return cls(id_=id_)


def _get_csrf_headers(csrf_token: str) -> dict[str, str]:
    # format headers for a spoofed AJAX request
    return {
        'accept': r'text/javascript',
        'x-csrf-token': csrf_token,
        'x-requested-with': 'XMLHttpRequest'
    }


def _check_login_result(r: Response):
    # Successful login is to redirect to https://home.planningcenteronline.com
    return (
            len(r.history) > 0 and
            r.history[0].status_code == 302 and
            r.history[0].headers['Location'] == _HOME_ROOT_URL
    )


class PlanningCenterBackend:
    def __init__(self):
        self._logged_in: bool = False
        self._username: Optional[str] = None
        self._session: Session = Session()

    def __repr__(self):
        return f'PlanningCenterBackend(logged_in={self._logged_in}, username={self._username})'

    def _check_login(self) -> bool:
        r = self._session.get(_TOPBAR_URL, headers=dict(accept='application/json'))
        # this will fail with 401 if we are not logged in
        self._logged_in = r.ok
        return self._logged_in

    def _get_authenticity_token(self, url: str) -> str:
        # get a valid authenticity token for login form
        # this will not work without the 'accept' header (*/* does not work)
        r_groups = self._session.get(url, headers=dict(accept='text/html'))
        soup = BeautifulSoup(r_groups.text, 'html.parser')
        authenticity_token = soup.find(attrs={'name': 'authenticity_token'}).attrs['value']
        return authenticity_token

    def _get_csrf_token(self, url: str) -> str:
        # get a valid csrf token for AJAX spoofing
        # this will not work without the 'accept' header (*/* does not work)
        r_groups = self._session.get(url, headers=dict(accept='text/html'))
        soup = BeautifulSoup(r_groups.text, 'html.parser')
        csrf_token = soup.find(attrs={'name': 'csrf-token'}).attrs['content']
        return csrf_token

    @property
    def logged_in(self) -> bool:
        return self._check_login()

    def login(self, username: str, password: str) -> bool:
        """
        Log in a requests session to Planning Center with given credentials.

        :param username: Username for login
        :param password: Password for login
        :return: Response object resulting from login post
        """
        # Get the needed authenticity token from the frontend
        authenticity_token = self._get_authenticity_token(_LOGIN_NEW_URL)
        # format post login request
        data = dict(
            authenticity_token=authenticity_token,
            login=username,
            password=password,
            commit='Sign in'
        )
        # Perform login
        r_login = self._session.post(_LOGIN_POST_URL, data=data)

        # both failed login and successful login return 200, so best is to check access to topbar resource
        if not r_login.ok:
            raise RuntimeError('Login post failed, unexpected even for unsuccessful login. Check API assumptions')

        if self.logged_in:
            self._username = username
            return True
        else:
            return False

    def logout(self):
        if not self.logged_in:
            return
        r = self._session.get(_LOGOUT_URL)
        success = not self.logged_in
        if success:
            self._username = None
        else:
            raise RuntimeError(f'Logout failed, Request Status: {r.status_code}')

    def create_group(self, name: str) -> GroupIdentifier:
        """
        Create a new Planning Center Small Group

        :param name: Name of new group
        :return: Identifier of new group resource
        """
        if not self.logged_in:
            raise ValueError('User is not logged in')

        # get AJAX security token from frontend
        csrf_token = self._get_csrf_token(_GROUPS_ROOT_URL)

        # format group creation post request
        data = {
            'group[name]': name,
            'group[group_type_id]': int(GroupType.SmallGroup)
        }
        # do group creation
        r = self._session.post(
            _GROUPS_BASE_URL,
            data=data,
            headers=_get_csrf_headers(csrf_token)
        )
        # check result
        if not r.ok:
            raise RuntimeError(f'New group creation failed, Response {r.status_code}')

        # get the new group uri
        group_location = r.headers['Location']

        return GroupIdentifier.from_url(group_location)

    def delete_group(self, group: GroupIdentifier) -> Response:
        """
        Delete the given group
        :param group: Identifier of group
        :return: Response object resulting from deletion
        """
        # get AJAX security token
        csrf_token = self._get_csrf_token(urljoin(group.frontend_url + '/', 'settings'))
        # perform deletion
        r = self._session.delete(group.frontend_url, headers=_get_csrf_headers(csrf_token))
        return r

    def get_group_info(self, group: GroupIdentifier) -> Dict[str, Any]:
        r = self._session.get(group.api_url)
        if not r.ok:
            raise ValueError(f'Failed to get group information from {group.api_url}')
        return json.loads(r.text)

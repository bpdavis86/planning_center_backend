from __future__ import annotations

from typing import Optional

import requests
from bs4 import BeautifulSoup
from requests import Session

from . import _urls as urls
from .groups import GroupsApiProvider


__all__ = ['PlanningCenterBackend']


def _get_csrf_headers(csrf_token: str) -> dict[str, str]:
    # format headers for a spoofed AJAX request
    return {
        'accept': r'text/javascript',
        'x-csrf-token': csrf_token,
        'x-requested-with': 'XMLHttpRequest'
    }


class PlanningCenterBackend:
    def __init__(self):
        self._logged_in: bool = False
        self._username: Optional[str] = None
        self._session: Session = Session()
        self.groups = GroupsApiProvider(self)

    def __repr__(self):
        return f'PlanningCenterBackend(logged_in={self._logged_in}, username={self._username})'

    def _check_login(self) -> bool:
        r = self._session.get(urls.TOPBAR_URL, headers=dict(accept='application/json'))
        # this will fail with 401 if we are not logged in
        self._logged_in = r.ok
        return self._logged_in

    def _get_authenticity_token(self, frontend_url: str) -> str:
        # get a valid authenticity token for login form
        # this will not work without the 'accept' header (*/* does not work)
        r_groups = self._session.get(frontend_url, headers=dict(accept='text/html'))
        soup = BeautifulSoup(r_groups.text, 'html.parser')
        authenticity_token = soup.find(attrs={'name': 'authenticity_token'}).attrs['value']
        return authenticity_token

    def get_csrf_token(self, frontend_url: str) -> str:
        # get a valid csrf token for AJAX spoofing
        # this will not work without the 'accept' header (*/* does not work)
        r_groups = self._session.get(frontend_url, headers=dict(accept='text/html'))
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
        authenticity_token = self._get_authenticity_token(urls.LOGIN_NEW_URL)
        # format post login request
        data = dict(
            authenticity_token=authenticity_token,
            login=username,
            password=password,
            commit='Sign in'
        )
        # Perform login
        r_login = self._session.post(urls.LOGIN_POST_URL, data=data)

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
        r = self._session.get(urls.LOGOUT_URL)
        success = not self.logged_in
        if success:
            self._username = None
        else:
            raise RuntimeError(f'Logout failed, Request Status: {r.status_code}')

    def get_json(self, url: str):
        r = self._session.get(url, headers=dict(accept='application/json'))
        if not r.ok:
            raise ValueError(f'Could not get content at {url}')
        return r.text

    def post(self, url: str, data: dict, csrf_token: Optional[str] = None) -> requests.Response:
        # do group creation
        if csrf_token is not None:
            r = self._session.post(
                url,
                data=data,
                headers=_get_csrf_headers(csrf_token)
            )
        else:
            r = self._session.post(
                url,
                data=data,
            )

        # check result
        if not r.ok:
            raise RuntimeError(f'Post to {url} failed, Response {r.status_code}')

        return r

    def delete(self, url: str, csrf_token: Optional[str] = None) -> requests.Response:
        if csrf_token:
            r = self._session.delete(url, headers=_get_csrf_headers(csrf_token))
        else:
            r = self._session.delete(url)

        # check result
        if not r.ok:
            raise RuntimeError(f'Delete of {url} failed, Response {r.status_code}')

        return r

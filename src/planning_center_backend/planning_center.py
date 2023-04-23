from __future__ import annotations

from typing import Optional

import requests
from bs4 import BeautifulSoup
from cachetools import cached, TTLCache
from requests import Session

from . import _urls as urls
from ._exceptions import RequestError
from .groups import GroupsApiProvider


__all__ = ['PlanningCenterBackend']


def _get_csrf_headers(csrf_token: str) -> dict[str, str]:
    # format headers for a spoofed AJAX request
    return {
        'accept': r'text/javascript',
        'x-csrf-token': csrf_token,
        'x-requested-with': 'XMLHttpRequest'
    }


# Cache CSRF tokens for one minute
CSRF_CACHE_TIME = 60  # sec


@cached(cache=TTLCache(maxsize=1024, ttl=CSRF_CACHE_TIME))
def _get_cached_csrf_token(session: requests.Session, url: str) -> str:
    return _get_csrf_token(session, url)


def _get_csrf_token(session: requests.Session, url: str) -> str:
    # get a valid csrf token for AJAX spoofing
    # this will not work without the 'accept' header (*/* does not work)
    r = session.get(url, headers=dict(accept='text/html'))
    if not r.ok:
        raise RequestError(f'Could not fetch page {url} for csrf_token', response=r)
    soup = BeautifulSoup(r.text, 'html.parser')
    csrf_token = soup.find(attrs={'name': 'csrf-token'}).attrs['content']
    return csrf_token


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

    def get_csrf_token(
            self,
            frontend_url: str,
            *,
            no_cache: bool = False,
            force_refresh: bool = False,
    ) -> str:
        """
        Get a CSRF token from given frontend url.

        :param frontend_url: URL of page from which to fetch token
        :param no_cache: Disable use of caching, default False
        :param force_refresh: Force expiration of current cache key for this url, default False
        :return: Token value
        """
        if force_refresh:
            # remove key from cache if present
            _get_cached_csrf_token.cache.pop((self._session, frontend_url), None)

        if no_cache:
            return _get_csrf_token(self._session, frontend_url)
        else:
            return _get_cached_csrf_token(self._session, frontend_url)

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

    def get_frontend_soup(self, url: str) -> BeautifulSoup:
        r = self._session.get(url, headers=dict(accept='text/html'))
        if not r.ok:
            raise RequestError(f'Could not get page content at {url}', response=r)
        return BeautifulSoup(r.text, 'html.parser')

    def get_json(self, url: str, params: Optional[dict] = None):
        r = self._session.get(url, headers=dict(accept='application/json'), params=params)
        if not r.ok:
            raise RequestError(f'Could not get JSON content at {url}', response=r)
        return r.text

    def post(
            self,
            url: str,
            data: dict,
            *,
            csrf_frontend_url: Optional[str] = None,
            csrf_no_cache: bool = False,
            csrf_auto_retry: bool = True,
    ) -> requests.Response:
        # do group creation
        if csrf_frontend_url is not None:
            csrf_token = self.get_csrf_token(csrf_frontend_url, no_cache=csrf_no_cache)
            r = self._session.post(
                url,
                data=data,
                headers=_get_csrf_headers(csrf_token)
            )
            if not r.ok and not csrf_no_cache and csrf_auto_retry:
                # retry request after expiring cached token
                csrf_token = self.get_csrf_token(csrf_frontend_url, force_refresh=True)
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
            raise RequestError(f'Post to {url} failed, Response {r.status_code}', response=r)

        return r

    def delete(
            self,
            url: str,
            *,
            csrf_frontend_url: Optional[str] = None,
            csrf_no_cache: bool = False,
            csrf_auto_retry: bool = True,
    ) -> requests.Response:
        if csrf_frontend_url:
            csrf_token = self.get_csrf_token(csrf_frontend_url, no_cache=csrf_no_cache)
            r = self._session.delete(url, headers=_get_csrf_headers(csrf_token))
            if not r.ok and not csrf_no_cache and csrf_auto_retry:
                # retry request after expiring cached token
                csrf_token = self.get_csrf_token(csrf_frontend_url, force_refresh=True)
                r = self._session.delete(url, headers=_get_csrf_headers(csrf_token))
        else:
            r = self._session.delete(url)

        # check result
        if not r.ok:
            raise RequestError(f'Delete of {url} failed, Response {r.status_code}', response=r)

        return r

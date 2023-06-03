from typing import Optional

from .._json_schemas.groups import PeopleSchema
from ..api_provider import ApiProvider
from .. import _urls as urls

__all__ = ['GroupsPeopleApiProvider']


class GroupsPeopleApiProvider(ApiProvider):
    def query(
            self,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
    ):
        # Note: this query will only return people who have ever interacted with the group system
        # i.e. have ever been added to a group and have a group add id associated with them.
        # We probably want to use the separate people system API to query people ids
        params = {}
        if first_name is not None:
            params['where[first_name]'] = first_name
        if last_name is not None:
            params['where[last_name]'] = last_name
        return self.query_api(urls.GROUPS_PEOPLE_URL, params=params, schema=PeopleSchema)

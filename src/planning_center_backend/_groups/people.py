from typing import Optional, Sequence

from .._json_schemas.groups import PeopleSchema, PersonData
from ..api_provider import ApiProvider
from .. import _urls as urls

__all__ = ['GroupsPeopleApiProvider']


class GroupsPeopleApiProvider(ApiProvider):
    """
    Provide API query access to people registered in the groups system.

    This is NOT the same as the global people database.
    This API can only see people who have ever participated in a group.
    General queries for people should use the top level People API (planning_center_backend.people).
    """
    def query(
            self,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
    ) -> Sequence[PersonData]:
        """
        Query Groups People API
        :param first_name: Optional first name for query filter
        :param last_name: Optional last name for query filter
        :return: List of people matching query
        """
        # Note: this query will only return people who have ever interacted with the group system
        # i.e. have ever been added to a group and have a group add id associated with them.
        # We probably want to use the separate people system API to query people ids
        params = {}
        if first_name is not None:
            params['where[first_name]'] = first_name
        if last_name is not None:
            params['where[last_name]'] = last_name
        return self.query_api(urls.GROUPS_PEOPLE_URL, params=params, schema=PeopleSchema)

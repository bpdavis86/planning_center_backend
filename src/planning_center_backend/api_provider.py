from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Mapping, Type

import msgspec

from ._json_schemas.base import ApiBase

if TYPE_CHECKING:
    # avoid circular import
    from .planning_center import PlanningCenterBackend


class ApiProvider:
    """
    Base class for all v2 API queries.
    Child classes should implement their own methods using the query_api method to drive the query.
    """
    def __init__(self, _backend: PlanningCenterBackend):
        self._backend = _backend

    def query_api(
            self,
            url: str,
            params: Optional[Mapping[str, Any]] = None,
            schema: Optional[Type[ApiBase]] = None,
            limit: Optional[int] = None
    ) -> Any:
        """
        Handle queries to the Planning Center API, including multi-record chunked results.

        Return value is either `schema.data` (for scalar query)
        or concatenation of `schema.data` over chunks (for multi-record query)

        :param url: API URL to query
        :param params: HTTP GET parameters for query
        :param schema: msgspec schema (derived from ApiBase) to be used to translate result
        :param limit: For multi-record results, data-set size limit
        :return: Query result data
        """
        # The API for a multi-dataset returns JSON in chunks
        # For every request, if links contains 'next', that is the URL
        # of next query chunk.
        results = []
        if schema is None:
            schema = ApiBase

        # Loop all the group chunks while we are pointed to a next URL
        while url:
            txt = self._backend.get_json(url, params)
            section = msgspec.json.decode(txt, type=schema)

            if 'total_count' not in section.meta:
                # result is a singleton, return now
                return section.data

            # result is a list and needs next processing
            results.extend(section.data)

            if section.links is not None and 'next' in section.links:
                url = section.links['next']
            else:
                url = None

            if limit is not None and len(results) >= limit:
                break

        return results

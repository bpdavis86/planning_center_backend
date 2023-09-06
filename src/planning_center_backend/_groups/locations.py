from typing import Sequence

from .. import _urls as urls
from .._json_schemas.groups import LocationsSchema, LocationData
from ..api_provider import ApiProvider

__all__ = ['LocationsApiProvider']


class LocationsApiProvider(ApiProvider):
    """
    Provide API v2 access to the registered locations.
    """
    def query(self) -> Sequence[LocationData]:
        """
        Query all locations. (This API does not support filter parameters)
        :return: LocationData list
        """
        return self.query_api(urls.GROUPS_LOCATIONS_URL, schema=LocationsSchema)

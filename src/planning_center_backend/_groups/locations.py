from typing import Sequence

from .. import _urls as urls
from .._json_schemas.groups import LocationsSchema, LocationData
from ..api_provider import ApiProvider

__all__ = ['LocationsApiProvider']


class LocationsApiProvider(ApiProvider):
    def query(self) -> Sequence[LocationData]:
        return self.query_api(urls.GROUPS_LOCATIONS_URL, schema=LocationsSchema)

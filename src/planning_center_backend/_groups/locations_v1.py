from enum import Enum
from typing import Sequence, Union, Optional, List, Tuple

import msgspec.json

from planning_center_backend.maps import GeocodeData
from planning_center_backend.api_provider import ApiProvider
from .._json_schemas.groups import LocationV1Response, LocationV1Data

__all__ = ['LocationV1ApiProvider']


class DisplayPreference(Enum):
    Exact = 'exact'
    Approximate = 'approximate'
    Hidden = 'hidden'


class LocationV1ApiProvider(ApiProvider):
    """
    Provide API v1 access to registered location settings.

    This API is currently preferred for setup of new locations because the v2 API does not have set access.
    """
    def __init__(self, _backend, _group_id: int):
        super().__init__(_backend)
        self._group_id = _group_id

    @property
    def settings_url(self) -> str:
        return f'https://groups.planningcenteronline.com/groups/{self._group_id}/settings'

    @property
    def locations_url(self) -> str:
        return f'https://groups.planningcenteronline.com/api/v1/groups/{self._group_id}/locations.json'

    def _get_delete_url(self, location_id: int) -> str:
        return f'https://groups.planningcenteronline.com/api/v1/groups/{self._group_id}/locations/{location_id}.json'

    def query(self) -> Sequence[LocationV1Data]:
        """
        Retrieve a list of all existing locations for this group to use, including name and id.
        :return: List of location data descriptors.
        """
        txt = self._backend.get_json(self.locations_url)
        results = msgspec.json.decode(txt, type=LocationV1Response)
        return results.locations

    def _create_base(
            self,
            name: str,
            formatted_address: str,
            latitude: Union[float, str],
            longitude: Union[float, str],
            display_preference: Union[DisplayPreference, str] = DisplayPreference.Approximate,
            shared: bool = True,
            approx_latitude: Optional[Union[float, str]] = None,
            approx_longitude: Optional[Union[float, str]] = None,
            radius: int = 1000,
            address_data: Optional[List[Tuple[str, str]]] = None,
    ) -> int:
        if isinstance(display_preference, str):
            display_preference = DisplayPreference(display_preference.lower())

        latitude = float(latitude)
        longitude = float(longitude)
        if approx_latitude is None:
            approx_latitude = round(latitude, 2)
        if approx_longitude is None:
            approx_longitude = round(longitude, 2)

        params = [
            ('location[display_preference]', display_preference.value),
            ('location[id]', 'new'),
            ('location[group_id]', '' if shared else str(self._group_id)),
            ('location[permissions][can_share]', 'true'),
            ('location[name]', name),
            ('location[formatted_address]', formatted_address),
            ('location[latitude]', str(latitude)),
            ('location[longitude]', str(longitude)),
            ('location[approximation][center][lat]', str(approx_latitude)),
            ('location[approximation][center][lng]', str(approx_longitude)),
            ('location[approximation][radius]', str(radius)),
        ]
        if address_data is not None:
            params.extend(address_data)

        r = self._backend.post(self.locations_url, data=params, csrf_frontend_url=self.settings_url)
        results = msgspec.json.decode(r.text, type=LocationV1Response)
        return results.id

    def create(
            self,
            name: str,
            geocode_data: GeocodeData,
            display_preference: Union[DisplayPreference, str] = DisplayPreference.Approximate,
            shared: bool = True,
            approx_latitude: Optional[Union[float, str]] = None,
            approx_longitude: Optional[Union[float, str]] = None,
            radius: int = 1000,
    ) -> int:
        """
        Add physical location to group meeting settings

        :param name: Name of location
        :param geocode_data: Geocode data for location queried from Google Maps API
        :param display_preference: Display behavior for non-members (default approximate)
        :param shared: Is this location shared with other groups (default true)
        :param approx_latitude: Approximate latitude to show in approximate display mode
            (default rounded from geocode data)
        :param approx_longitude: Approximate longitude to show in approximate display mode
            (default rounded from geocode data)
        :param radius: Approximate location display radius (default 1000)
        :return: Location id of new group location
        """
        # we need to do the work of translating the Google Geocode data
        formatted_address = geocode_data.formatted_address
        latitude = geocode_data.geometry.location.lat
        longitude = geocode_data.geometry.location.lng
        address_data = []
        for i, c in enumerate(geocode_data.address_components):
            address_data.append((f'location[address_data][{i}][long_name]', c.long_name))
            address_data.append((f'location[address_data][{i}][short_name]', c.short_name))
            for t in c.types:
                address_data.append((f'location[address_data][{i}][types][]', t))

        return self._create_base(
            name=name,
            formatted_address=formatted_address,
            latitude=latitude,
            longitude=longitude,
            display_preference=display_preference,
            shared=shared,
            approx_longitude=approx_longitude,
            approx_latitude=approx_latitude,
            radius=radius,
            address_data=address_data
        )

    def create_custom(
            self,
            name: str,
            formatted_address: str,
            latitude: Union[float, str],
            longitude: Union[float, str],
            display_preference: Union[DisplayPreference, str] = DisplayPreference.Approximate,
            shared: bool = True,
            approx_latitude: Optional[Union[float, str]] = None,
            approx_longitude: Optional[Union[float, str]] = None,
            radius: int = 1000,
    ) -> int:
        """
        Add custom physical location to group meeting settings (not based on Google Maps data).

        :param name: Name of location
        :param formatted_address: Display address of location
        :param latitude: Exact latitude of location
        :param longitude: Exact longitude of location
        :param display_preference: Display behavior for non-members (default approximate)
        :param shared: Is this location shared with other groups (default true)
        :param approx_latitude: Approximate latitude to show in approximate display mode
            (default rounded from latitude)
        :param approx_longitude: Approximate longitude to show in approximate display mode
            (default rounded from longitude)
        :param radius: Approximate location display radius (default 1000)
        :return: Location id of new group location
        """

        address_data = [
            ('location[address_data][0][long_name]', formatted_address),
            ('location[address_data][0][short_name]', formatted_address),
            ('location[address_data][0][types][]', 'custom'),
            ('location[address_data][0][types][]', 'full_address'),
        ]

        return self._create_base(
            name=name,
            formatted_address=formatted_address,
            latitude=latitude,
            longitude=longitude,
            display_preference=display_preference,
            shared=shared,
            approx_longitude=approx_longitude,
            approx_latitude=approx_latitude,
            radius=radius,
            address_data=address_data
        )

    def delete(self, location_id: int) -> None:
        """
        Remove a location from the shared location list or the location list for this group.
        :param location_id: Identifier of location to remove
        :return:
        """
        self._backend.delete(self._get_delete_url(location_id), csrf_frontend_url=self.settings_url)

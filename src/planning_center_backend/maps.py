from __future__ import annotations

from typing import List, Optional

import requests
import msgspec

from planning_center_backend._exceptions import RequestError


class GoogleResponse(msgspec.Struct):
    status: str
    error_message: Optional[str] = None

    def check(self):
        if self.status not in ['OK', 'ZERO_RESULTS']:
            error_message = self.error_message if self.error_message is not None else ''
            raise ValueError(f'Google API request failed with code {self.status} and message "{error_message}"')


class FindPlaceResponse(GoogleResponse, kw_only=True):
    candidates: List[FindPlaceData]


class FindPlaceData(msgspec.Struct):
    formatted_address: str
    name: str
    place_id: str


class GeocodeResponse(GoogleResponse, kw_only=True):
    results: List[GeocodeData]


class GeocodeData(msgspec.Struct):
    address_components: List[AddressComponent]
    formatted_address: str
    geometry: Geometry
    place_id: str
    types: List[str]


class AddressComponent(msgspec.Struct):
    long_name: str
    short_name: str
    types: List[str]


class Geometry(msgspec.Struct):
    location: LatLong
    location_type: str
    viewport: Optional[LatLongBounds] = None
    bounds: Optional[LatLongBounds] = None


class LatLong(msgspec.Struct):
    lat: float
    lng: float


class LatLongBounds(msgspec.Struct):
    northeast: LatLong
    southwest: LatLong


class Maps:
    """
    This is a limited integration with Google Maps API to support group location setup
    as is done on Planning Center website.

    The user must supply his own Google Maps API key.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def find_place_from_text(self, text: str) -> List[FindPlaceData]:
        """
        Find a place name from input text (e.g. address)
        :param text:
        :return:
        """
        url = r'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        fields = ['formatted_address', 'name', 'place_id']
        params = {
            'key': self.api_key,
            'input': text,
            'inputtype': 'textquery',
            'fields': ','.join(fields)
        }
        r = requests.get(url, headers=dict(accept='application/json'), params=params)
        if not r.ok:
            raise RequestError('Request failed', r)
        response = msgspec.json.decode(r.text, type=FindPlaceResponse)
        response.check()
        return response.candidates

    def geocode_from_place_id(self, place_id: str) -> List[GeocodeData]:
        url = r'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'key': self.api_key,
            'place_id': place_id,
        }
        r = requests.get(url, headers=dict(accept='application/json'), params=params)
        if not r.ok:
            raise RequestError('Request failed', r)
        response = msgspec.json.decode(r.text, type=GeocodeResponse)
        response.check()
        return response.results

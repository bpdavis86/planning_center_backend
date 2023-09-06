import pytest

from planning_center_backend import maps


@pytest.fixture(scope="module")
def maps_api(maps_api_key) -> maps.Maps:
    return maps.Maps(maps_api_key)


def test_find_place_from_text(maps_api):
    places = maps_api.find_place_from_text('1100 Mid City Dr, 35806')
    assert len(places) == 1
    assert places[0].formatted_address == '1100 Mid City Dr, Huntsville, AL 35806, USA'


def test_geocode_from_place_id(maps_api):
    places = maps_api.find_place_from_text('1100 Mid City Dr, 35806')
    assert len(places) == 1
    geocodes = maps_api.geocode_from_place_id(places[0].place_id)
    assert len(geocodes) == 1
    assert geocodes[0].place_id == places[0].place_id

import os
from random import randrange

import pytest
import keyring
import keyring.credentials

import planning_center_backend.groups
from planning_center_backend import planning_center


def _get_keyring_credential(name, kind):
    cred = keyring.get_credential(name, None)
    if cred is None:
        raise ValueError(f'Please configure your {kind} in keyring under credential name "{name}"')
    return cred


@pytest.fixture(scope="session")
def credentials() -> keyring.credentials.Credential:
    return _get_keyring_credential('planningcenteronline.com', 'Planning Center Login')


@pytest.fixture(scope="session")
def maps_api_key() -> str:
    return _get_keyring_credential('maps-api:https://maps.googleapis.com', 'Google Maps API key').password


@pytest.fixture(scope="session")
def backend_session(credentials: keyring.credentials.Credential) -> planning_center.PlanningCenterBackend:
    b = planning_center.PlanningCenterBackend()
    success = b.login(credentials.username, credentials.password)
    if not success:
        raise ValueError('Unable to login to Planning Center with provided credentials')
    yield b
    b.logout()


@pytest.fixture(scope="session")
def test_group_id() -> int:
    id_ = os.getenv('PLANNING_CENTER_TEST_GROUP_ID')
    if id_ is None:
        raise ValueError('PLANNING_CENTER_TEST_GROUP_ID is not set')
    return int(id_)


@pytest.fixture(scope="session")
def test_group(backend_session, test_group_id) -> planning_center_backend.groups.GroupObject:
    group = backend_session.groups.get(test_group_id)
    return group


@pytest.fixture(scope="session")
def run_id() -> int:
    return randrange(65535)

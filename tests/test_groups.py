from datetime import date, timedelta

import pytest
from planning_center_backend import planning_center
from planning_center_backend.groups import GroupType, GroupEnrollment, GroupLocationType, GroupEventsVisibility


def test_get(backend_session: planning_center.PlanningCenterBackend, test_group_id: int):
    group = backend_session.groups.get(test_group_id)
    assert group.id_.id_ == test_group_id


def test_get_all(backend_session: planning_center.PlanningCenterBackend, test_group_id: int):
    groups = backend_session.groups.get_all()
    assert groups


def _property_tester(obj, attr, value):
    old = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        assert getattr(obj, attr) == value
    finally:
        setattr(obj, attr, old)


class TestGroup:
    def test_deleted(self, test_group):
        assert not test_group.deleted

    def test_memberships(self, test_group):
        assert test_group.memberships

    def test_events(self, test_group):
        assert test_group.events

    def test_tags(self, test_group):
        assert test_group.tags

    def test_name(self, test_group, run_id):
        _property_tester(test_group, 'name', f'Test Name {run_id}')

    def test_description(self, test_group, run_id):
        _property_tester(test_group, 'description', f'<div>Updated description {run_id}.</div>')

    @pytest.mark.parametrize('value', [
        GroupType.SmallGroup, GroupType.SeasonalClasses, GroupType.Online, GroupType.Unique
    ])
    def test_group_type(self, test_group, value):
        _property_tester(test_group, 'group_type', value)

    def test_schedule(self, test_group, run_id):
        _property_tester(test_group, 'schedule', f'Test Schedule {run_id}')

    @pytest.mark.parametrize('value', [True, False])
    def test_publicly_display_meeting_schedule(self, test_group, value):
        _property_tester(test_group, 'publicly_display_meeting_schedule', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_publicly_visible(self, test_group, value):
        _property_tester(test_group, 'publicly_visible', value)

    @pytest.mark.parametrize('value', [
        GroupEnrollment.Closed, GroupEnrollment.OpenSignup, GroupEnrollment.RequestToJoin
    ])
    def test_enrollment_strategy(self, test_group, value):
        _property_tester(test_group, 'enrollment_strategy', value)

    def test_contact_email(self, test_group, run_id):
        _property_tester(test_group, 'contact_email', f'tester{run_id}@foo.com')

    @pytest.mark.parametrize('value', [True, False])
    def test_default_event_automated_reminders_enabled(self, test_group, value):
        _property_tester(test_group, 'default_event_automated_reminders_enabled', value)

    @pytest.mark.parametrize('value', [1, 3, 10])
    def test_default_event_automated_reminders_schedule_offset(self, test_group, value):
        _property_tester(test_group, 'default_event_automated_reminders_schedule_offset', value)

    @pytest.mark.parametrize('value', [
        GroupLocationType.Virtual, GroupLocationType.Physical
    ])
    def test_location_type_preference(self, test_group, value):
        _property_tester(test_group, 'location_type_preference', value)

    @pytest.mark.parametrize('value', [
        None,  # (no location)
        797809  # Davis Home
    ])
    def test_location_id(self, test_group, value):
        _property_tester(test_group, 'location_id', value)

    def test_virtual_location_url(self, test_group, run_id):
        _property_tester(test_group, 'virtual_location_url', f'http://testurl{run_id}.foo.com')

    @pytest.mark.parametrize('value', [GroupEventsVisibility.Public, GroupEventsVisibility.Members])
    def test_events_visibility(self, test_group, value):
        _property_tester(test_group, 'events_visibility', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_leader_name_visible_on_public_page(self, test_group, value):
        _property_tester(test_group, 'leader_name_visible_on_public_page', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_communication_enabled(self, test_group, value):
        _property_tester(test_group, 'communication_enabled', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_members_can_create_forum_topics(self, test_group, value):
        _property_tester(test_group, 'members_can_create_forum_topics', value)

    @pytest.mark.parametrize('value', [None, date.today() + timedelta(days=1)])
    def test_enrollment_open_until(self, test_group, value):
        _property_tester(test_group, 'enrollment_open_until', value)

    @pytest.mark.parametrize('value', [None, 5, 10])
    def test_enrollment_limit(self, test_group, value):
        _property_tester(test_group, 'enrollment_limit', value)

    @pytest.mark.parametrize('value', [None, 5, 10])
    def test_member_limit_maximum_alert(self, test_group, value):
        _property_tester(test_group, 'member_limit_maximum_alert', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_request_event_attendance_from_leaders(self, test_group, value):
        _property_tester(test_group, 'request_event_attendance_from_leaders', value)

    @pytest.mark.parametrize('value', [
        None,
        2084403,  # Cody Phillips
    ])
    def test_attendance_reply_to_person_id(self, test_group, value):
        _property_tester(test_group, 'attendance_reply_to_person_id', value)

    @pytest.mark.parametrize('value', [True, False])
    def test_leaders_can_search_people_database(self, test_group, value):
        _property_tester(test_group, 'leaders_can_search_people_database', value)

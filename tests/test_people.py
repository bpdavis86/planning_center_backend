from planning_center_backend.people import PeopleQueryExpression

TEST_NAME = 'Benjamin Davis'
TEST_ID = 71655284


class TestGroup:
    def test_query(self, backend_session):
        qe = PeopleQueryExpression(search_name=TEST_NAME)
        d = backend_session.people.query(qe)
        assert len(d.data) == 1
        assert int(d.data[0].id) == TEST_ID

    def test_get(self, backend_session):
        d = backend_session.people.get(TEST_ID)
        assert int(d.data.id) == TEST_ID

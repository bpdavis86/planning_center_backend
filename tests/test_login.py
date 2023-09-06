def test_login(backend_session):
    assert backend_session.logged_in

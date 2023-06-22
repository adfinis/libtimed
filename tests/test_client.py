from datetime import timedelta


def test_overtime(client):
    result = client.overtime.get()
    assert isinstance(result, timedelta)
    result = client.overtime.get(raw=True)
    assert isinstance(result, dict)


def test_users(client):
    result = client.users.get()
    assert all(isinstance(user, dict) for user in result)

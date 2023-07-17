import pytest

from libtimed.models import GetOnlyMixin


def test_get_only_mixin(client):
    with pytest.raises(NotImplementedError) as exc_info:
        client.users.post()
    assert exc_info.value.args[0] == GetOnlyMixin.message


def test_includes(client):
    overtime = client.overtime.get(include="user")
    assert overtime[0]["relationships"]["user"]["id"] == client.users.me["id"]
    raw_overtime = client.overtime.get(include="user", raw=True)
    assert raw_overtime["data"] == overtime

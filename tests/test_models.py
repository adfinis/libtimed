import pytest

from libtimed.models import GetOnlyMixin


def test_get_only_mixin(client):
    with pytest.raises(NotImplementedError) as exc_info:
        client.users.post()

    assert exc_info.value.args[0] == GetOnlyMixin.message


def test_includes(client):
    overtime = client.overtime.get(include="user")
    assert overtime["relationships"]["user"] == client.users.me


def test_parse_defaults():
    assert True


def test_parse_relationships():
    assert True

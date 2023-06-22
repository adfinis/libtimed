from datetime import timedelta

import pytest

from libtimed.utils import deserialize_duration, serialize_duration


@pytest.mark.parametrize(
    "duration,result",
    [
        ("04:30:00", timedelta(hours=4, minutes=30)),
        ("-1 19:30:00", timedelta(days=-1, hours=19, minutes=30)),
        ("1 03:30:00", timedelta(days=1, hours=3, minutes=30)),
    ],
)
def test_parse_duration(duration, result):
    assert deserialize_duration(duration) == result
    assert serialize_duration(result) == duration

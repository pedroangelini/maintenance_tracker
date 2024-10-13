import pytest
from utils import (
    _round_datetime,
    _round_interval,
    parse_date,
    parse_interval,
    human_interval_str,
)
from datetime import datetime, timedelta, date


@pytest.mark.parametrize(
    "message,input,expected",
    [
        (
            "round down",
            datetime(2024, 1, 2, 10, 20, 1),
            datetime(2024, 1, 2, 10, 20, 0),
        ),
        (
            "round up",
            datetime(2024, 1, 2, 10, 20, 31),
            datetime(2024, 1, 2, 10, 21, 0),
        ),
        (
            "no round needed",
            datetime(2024, 1, 2, 10, 20),
            datetime(2024, 1, 2, 10, 20, 0),
        ),
    ],
)
def test__round_datetime(
    message: str,
    input: datetime,
    expected: datetime,
):
    assert _round_datetime(input) == expected, message


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            "today",
            _round_datetime(datetime.now().astimezone()),
        ),
        (
            "1 month",
            _round_datetime(
                datetime.now().replace(month=date.today().month + 1)
            ).astimezone(),
        ),
    ],
)
def test_parse_date(input: str, expected: datetime):
    assert parse_date(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            timedelta(days=2),
            "2 days",
        ),
        (
            timedelta(minutes=25),
            "25 minutes",
        ),
        (
            timedelta(days=7),
            "7 days",
        ),
        (timedelta(weeks=4), "28 days"),
        (timedelta(days=61), "2 months"),
        (timedelta(days=30), "30 days"),
        (timedelta(days=31), "1 month and 0 days"),
    ],
)
def test_human_interval_str(input: timedelta, expected: str):
    assert human_interval_str(input) == expected

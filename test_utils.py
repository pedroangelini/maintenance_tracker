from datetime import UTC, date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from time import sleep

import pytest
from freezegun import freeze_time

from utils import (
    DateParseError,
    IntervalParseError,
    _round_datetime,
    _round_interval,
    human_date_str,
    human_interval_str,
    parse_date,
    parse_interval,
    parse_partial_timestamp,
)


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
            _round_datetime(datetime.now() + relativedelta(months=1)).astimezone(),
        ),
    ],
)
def test_parse_date(input: str, expected: datetime):
    assert parse_date(input) == expected


@pytest.mark.parametrize(
    "input",
    ["blargos", "a number of days"],
)
def test_parse_date_raises(
    input: str,
):
    with pytest.raises(DateParseError):
        parse_date(input)


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
        (None, "no interval provided"),
    ],
)
def test_human_interval_str(input: timedelta, expected: str):
    assert human_interval_str(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (  # nearest minute
            timedelta(days=1, seconds=63),
            timedelta(days=1, seconds=60),
        ),
        (  # nearest minute
            timedelta(days=1, seconds=59),
            timedelta(days=1, seconds=60),
        ),
        (  # nearest second
            timedelta(days=0, seconds=59, milliseconds=30),
            timedelta(days=0, seconds=59),
        ),
    ],
)
def test__round_interval(input: timedelta, expected: timedelta):
    assert _round_interval(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            None,
            timedelta(seconds=0),
        ),
        (
            "two minutes",
            timedelta(seconds=120),
        ),
        (
            "two minutes, 29 seconds",
            timedelta(seconds=120),
        ),
        (
            "29 seconds",
            timedelta(seconds=29),
        ),
        (
            "1 day",
            timedelta(days=1),
        ),
        (
            "30 days",
            timedelta(days=30),
        ),
    ],
)
def test_parse_interval(input: str, expected: timedelta):
    assert parse_interval(input) == expected


@pytest.mark.parametrize(
    "input",
    ["blargos", "a number of days"],
)
def test_parse_interval_raises(
    input: str,
):
    with pytest.raises(IntervalParseError):
        parse_interval(input)


@pytest.mark.parametrize(
    "delta,expected",
    [
        (None, "no date provided"),
        (timedelta(seconds=0), "now"),
        (timedelta(days=-1), "a day ago"),
        (timedelta(days=1), "a day from now"),
        (timedelta(hours=5), "5 hours from now"),
    ],
)
def test_human_date_str(delta, expected):
    frozen_time = datetime(2025, 3, 23, 19, 14, 00)
    with freeze_time(frozen_time):
        if delta is None:
            test_input = None
        else:
            test_input = datetime.now() + delta
        assert human_date_str(test_input, when_now=frozen_time) == expected


def test_parse_partial_timestamp():
    from utils import parse_partial_timestamp, UTC

    # Year
    start, end = parse_partial_timestamp("2024")
    assert start == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert end == datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)

    # Month
    start, end = parse_partial_timestamp("2024-05")
    assert start == datetime(2024, 5, 1, 0, 0, 0, tzinfo=UTC)
    assert end == datetime(2024, 5, 31, 23, 59, 59, 999999, tzinfo=UTC)

    # Day
    start, end = parse_partial_timestamp("2024-05-15")
    assert start == datetime(2024, 5, 15, 0, 0, 0, tzinfo=UTC)
    assert end == datetime(2024, 5, 15, 23, 59, 59, 999999, tzinfo=UTC)

    # Hour
    start, end = parse_partial_timestamp("2024-05-15 14")
    assert start == datetime(2024, 5, 15, 14, 0, 0, tzinfo=UTC)
    assert end == datetime(2024, 5, 15, 14, 59, 59, 999999, tzinfo=UTC)


@pytest.mark.parametrize("value", ["2024-05-15 14:30", "2024-05-15T14:30"])
def test_parse_partial_timestamp_minute_precision(value):
    start, end = parse_partial_timestamp(value)

    assert start == datetime(2024, 5, 15, 14, 30, 0, tzinfo=UTC)
    assert end == datetime(2024, 5, 15, 14, 30, 59, 999999, tzinfo=UTC)

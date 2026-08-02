from datetime import datetime, timedelta, UTC
import dateparser
import human_readable


class DateParseError(ValueError):
    pass


class IntervalParseError(ValueError):
    pass


def _round_datetime(precise_datetime: datetime) -> datetime:
    "rounds datetime to the nearest minute"
    return datetime(
        year=precise_datetime.year,
        month=precise_datetime.month,
        day=precise_datetime.day,
        hour=precise_datetime.hour,
        minute=round(precise_datetime.minute + precise_datetime.second / 60),
        tzinfo=precise_datetime.tzinfo,
    )


def parse_date(input: str) -> datetime:

    parsed = dateparser.parse(
        input,
        settings={"RETURN_AS_TIMEZONE_AWARE": True, "PREFER_DATES_FROM": "future"},
    )
    if parsed is None:
        raise DateParseError(f"Could not parse date '{input}'")
    return _round_datetime(parsed)


def parse_partial_timestamp(input_str: str) -> tuple[datetime, datetime]:
    """Parses a partial timestamp (like YYYY, YYYY-MM, YYYY-MM-DD) into a start and end datetime range in UTC."""
    import re

    s = input_str.strip()

    # YYYY
    m = re.match(r"^(\d{4})$", s)
    if m:
        year = int(m.group(1))
        start = datetime(year, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)
        return start, end

    # YYYY-MM or YYYY/MM
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        start = datetime(year, month, 1, 0, 0, 0, tzinfo=UTC)
        next_year = year + 1 if month == 12 else year
        next_month = 1 if month == 12 else month + 1
        end = datetime(next_year, next_month, 1, 0, 0, 0, tzinfo=UTC) - timedelta(
            microseconds=1
        )
        return start, end

    # YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        start = datetime(year, month, day, 0, 0, 0, tzinfo=UTC)
        end = datetime(year, month, day, 23, 59, 59, 999999, tzinfo=UTC)
        return start, end

    # YYYY-MM-DD HH or YYYY-MM-DDTHH
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2})$", s)
    if m:
        year, month, day, hour = (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
        )
        start = datetime(year, month, day, hour, 0, 0, tzinfo=UTC)
        end = datetime(year, month, day, hour, 59, 59, 999999, tzinfo=UTC)
        return start, end

    # YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})$", s)
    if m:
        year, month, day, hour, minute = (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            int(m.group(5)),
        )
        start = datetime(year, month, day, hour, minute, 0, tzinfo=UTC)
        end = datetime(year, month, day, hour, minute, 59, 999999, tzinfo=UTC)
        return start, end

    parsed = parse_date(s)
    return parsed, parsed


def _round_interval(precise_interval: timedelta) -> timedelta:
    """rounds timedelta to the nearest minute, except if an
    interval smaller than 1 min was given, in which case rounds to the
    nearest second
    """
    secs = precise_interval.total_seconds()
    if secs < 60:  # less than a minute, round to the closest second
        return timedelta(seconds=round(secs))

    # otherwise round to the nearest minute
    return timedelta(minutes=round(secs / 60))


def parse_interval(input: str) -> timedelta:
    """Parses a string into an interval

    Args:
        input (str): string to parse

    Raises:
        IntervalParseError: raised if the dateparser library could not parse this as an interval

    Returns:
        timedelta: rounded timedelta
    """
    if not input or input == "0":
        return timedelta(seconds=0)

    now = datetime.now(UTC)
    parsed = dateparser.parse(
        input,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",  # set as UTC to ensure it's consistent with "now"
            "PREFER_DATES_FROM": "future",
        },
    )
    if parsed is None:
        raise IntervalParseError(f"Could not parse interval '{input}'")

    # because we take now and parsed at slightly different times (milliseconds),
    return _round_interval(parsed - now)


def human_date_str(input: datetime | None, when_now: datetime | None = None) -> str:
    """Returns a human readable string representing the date

    Args:
        input (datetime | None): the datetime in question
        when_now (datetime | None): the time to consider as 'now'

    Returns:
        str: a human-readable version of the date time, such as "x hours from now"
    """
    if input is None:
        return "no date provided"

    if when_now is None:
        when_now = datetime.now().astimezone()

    if input.tzinfo is not None:
        input = input.replace(tzinfo=None)
    if when_now.tzinfo is not None:
        when_now = when_now.replace(tzinfo=None)

    if abs(input - when_now) <= timedelta(days=1):
        return human_readable.date_time(
            input,
            minimum_unit="SECONDS",
        )
    else:
        return human_readable.date(input.date() + timedelta(milliseconds=1))


def human_interval_str(
    input: timedelta | None, when_now: datetime | None = None
) -> str:

    if input is None:
        return "no interval provided"
    ret = human_readable.precise_delta(input)
    return ret

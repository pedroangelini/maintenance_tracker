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


def human_date_str(input: datetime | None) -> str:
    """Returns a human readable string representing the date

    Args:
        input (datetime | None): the datetime in question

    Returns:
        str: a human-readable version of the date time, such as "x hours from now"
    """
    if input is None:
        return "no date provided"
    if abs(input - datetime.now().astimezone()) <= timedelta(days=1):
        return human_readable.date_time(
            input.replace(tzinfo=None),  # timezone hack so the human_readable works
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

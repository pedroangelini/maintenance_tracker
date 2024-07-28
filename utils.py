from datetime import datetime, timedelta, UTC
import dateparser
import human_readable


class DateParseError(ValueError):
    pass


class IntervalParseError(ValueError):
    pass


def parse_date(input: str) -> datetime:
    parsed = dateparser.parse(input, settings={"RETURN_AS_TIMEZONE_AWARE": True})
    if parsed is None:
        raise DateParseError(f"Could not parse date '{input}'")
    return parsed


def _round_interval(precise_interval: timedelta) -> timedelta:
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
    if not input:
        return timedelta(seconds=0)

    now = datetime.now(UTC)
    parsed = dateparser.parse(
        input,
        settings={"RETURN_AS_TIMEZONE_AWARE": True, "PREFER_DATES_FROM": "future"},
    )
    if parsed is None:
        raise IntervalParseError(f"Could not parse interval '{input}'")

    # because we take now and parsed at slightly different times (miliseconds),
    return _round_interval(parsed - now)


def human_date_str(input: datetime | None, when_now: datetime | None = None) -> str:
    if input is None:
        return "no date provided"
    if when_now is None:
        when_now = datetime.now(tz=UTC)
    if abs(input - when_now) < timedelta(days=1):
        return human_readable.date_time(input, minimum_unit="minutes")
    else:
        return human_readable.date(input.date())


def human_interval_str(
    input: timedelta | None, when_now: datetime | None = None
) -> str:
    if input is None:
        return "no interval provided"
    if when_now is None:
        when_now = datetime.now(tz=UTC)
    if input < timedelta(days=1):
        return human_readable.date_time(input, future=True)
    else:
        return human_readable.date_time(input, future=True)

from datetime import datetime, timedelta, UTC
import dateparser


class DateParseError(ValueError):
    pass


class IntervalParseError(ValueError):
    pass


def parse_date(input: str) -> datetime:
    parsed = dateparser.parse(input, settings={"RETURN_AS_TIMEZONE_AWARE": True})
    if parsed is None:
        raise DateParseError(f"Could not parse date '{input}'")
    return parsed


def _round_interval(precise_int: timedelta) -> timedelta:
    secs = precise_int.total_seconds()
    if secs < 60:  # less than a minute, round to the closest second
        return timedelta(seconds=round(secs))

    # otherwise round to the nearest minute
    return timedelta(minutes=round(secs / 60))


def parse_interval(input: str) -> timedelta:
    now = datetime.now(UTC)
    parsed = dateparser.parse(
        input,
        settings={"RETURN_AS_TIMEZONE_AWARE": True, "PREFER_DATES_FROM": "future"},
    )
    if parsed is None:
        raise IntervalParseError(f"Could not parse interval '{input}'")

    # because we take now and parsed at slightly different times (miliseconds),
    return _round_interval(parsed - now)

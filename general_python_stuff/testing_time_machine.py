"""
Allows test modules to easily mock the result of calls to time.time()

Because other functions, such as datetime.now() rely on time.time() internally,
those functions and methods are also affected by the mock.

Example:
    >>> with at_date(year=1999, month=4, day=12):
    ...     print datetime.today()
    1999-12-04

Please note that this module only works in local time, and does not deal with
any timezone shenanigans.
"""

from unittest import mock
import time
from datetime import datetime
from contextlib import contextmanager

EPOCH = datetime.fromtimestamp(0)
"""The Unix Epoch is Jan. 1, 1970 GMT.  This is the local time equivalent."""


@contextmanager
def offset_time(days=0, hours=0, minutes=0, seconds=0):
    """CONTEXT MANAGER: Offset the results of time.time by the given amounts.

    Args:
        days (int): days to offset the current time by
        hours (int): hours to offset the current time by
        minutes (int): minutes to offset the current time by
        seconds (int): seconds to offset the current time by
    """
    hours = (days * 24) + hours
    minutes = (hours * 60) + minutes
    seconds = (minutes * 60) + seconds
    _unpatched_time = time.time

    def time_as_offset():
        return _unpatched_time() + seconds

    with mock.patch("time.time", new=time_as_offset):
        yield


def future_by(days=0, hours=0, minutes=0, seconds=0):
    """Offsets the result of time.time() into the future by the given amounts.

    Args:
        days (int): days to offset the current time by
        hours (int): hours to offset the current time by
        minutes (int): minutes to offset the current time by
        seconds (int): seconds to offset the current time by
    """
    return offset_time(days, hours, minutes, seconds)


def past_by(days=0, hours=0, minutes=0, seconds=0):
    """Offsets the result of time.time() into the past by the given amounts.

    Args:
        days (int): days to offset the current time by
        hours (int): hours to offset the current time by
        minutes (int): minutes to offset the current time by
        seconds (int): seconds to offset the current time by
    """
    return offset_time(-days, -hours, -minutes, -seconds)


def at_date_time(year=None, month=None, day=None, hour=None, minute=None,
                 second=None):
    """Patches time.time to be on a different date and time.

    If any argument is not supplied, current time values will be used

    Args:
        year (int)
        month (int)
        day (int)
    """
    dt = datetime.now()
    year = year if year is not None else dt.year
    month = month if month is not None else dt.month
    day = day if day is not None else dt.day
    hour = hour if hour is not None else dt.hour
    minute = minute if minute is not None else dt.minute
    second = second if second is not None else dt.second
    new_dt = datetime(year, month, day, hour, minute, second, microsecond=0)
    return at_datetime_obj(new_dt)


@contextmanager
def at_datetime_obj(datetime_obj):
    """CONTEXT MANAGER: Activates the Flux Capacitor.

    While the manager is active, calls to time.time() will return the epoch
    time for the given datetime object rather than the current time.

    Args:
        datetime_obj (datetime.datetime)
    """
    new_time = (datetime_obj - EPOCH).total_seconds()
    with mock.patch("time.time", return_value=new_time):
        yield

"""Base module for logging operations.

Setting up logging is easy!  In any module you want to log from, just follow
this pattern::

    import lumberjack
    logger = lumberjack.get_logger(__name__)
    logger.info("hello world")

At the top level of your application, you'll want to configure logging so
that your log message go where they need to.  You can also customize the
output by including a formatter and a severity threshold::

    import lumberjack
    lumberjack.add_console_output(formatter=lumberjack.Formatters.DATED)
    lumberjack.set_severity(lumberjack.Severity.DEBUG)

"""

import logging


class FileHandler(logging.FileHandler):
    """Monkey-patch. Modifies the behavior of logging.FileHandler._open() to
    support directory creation."""

    def _open(self):
        """
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        """
        # Creates the parent directory before attempting to return the file
        # stream, if one doesn't exist.
        if not os.path.isdir(os.path.dirname(self.baseFilename)):
            os.makedirs(os.path.dirname(self.baseFilename))
        return super(FileHandler, self)._open()


# Re-defines logging.FileHandler. From here on out, objects that inherit from
# logging.FileHandler will reference our custom version. This has to be done
# before importing anything else.
logging.FileHandler = FileHandler


import logging.handlers
import inspect
import enum
import time
import os
import glob

from python_utils import caching
from python_utils import inspections
from contextlib import contextmanager

# aliases
StreamHandler = logging.StreamHandler


__all__ = [
    "FileHandler", "StreamHandler", "BasicFileLogHandler",
    "LOGGER_NAME", "DEFAULT_LOG_LEVEL", "BaseLoggerAdapter",
    "get_base_logger", "get_logger", "Severity", "Interval",
    "log_formatter", "Formatters", "basic_formatter", "dated_formatter",
    "detail_formatter", "StackFilter", "set_severity", "add_handler",
    "add_console_output", "add_file_output", "get_valid_base_handlers"
]

LOGGER_NAME = "_lumberjack_"

DEFAULT_LOG_LEVEL = logging.INFO

_level_filters = dict()

_logger_cache = dict()


# BASE LOGGERS

class BaseLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, base_logger):

        # TODO:  Here, we can add extra contextual information, such as
        #        which project the code is running in
        extra = dict()
        self.base_logger = base_logger
        super(BaseLoggerAdapter, self).__init__(base_logger, extra)

    def addHandler(self, handler):
        self.logger.addHandler(handler)

    @property
    def handlers(self):
        return self.logger.handlers

    @property
    def valid_base_handlers(_):
        return get_valid_base_handlers()


@caching.constant
def get_base_logger():
    """Retrieve the base logger.

    This logger instance will live above any module-level loggers, but
    below the built-in python root logger.

    Returns:
        logging.LoggingAdapter: An adapter to the base logger. The adapter
        makes environment information available to the formatter.
    """

    base_logger = logging.getLogger(LOGGER_NAME)

    # The base logger is always configured to accept all
    # messages. All severity filtering is done by the handlers.
    base_logger.setLevel(logging.DEBUG)

    return BaseLoggerAdapter(base_logger)


def get_logger(name):
    """Obtains a named logger under the Base Logger

    Args:
        name (str): The name of the logger.  Follows the same rules as the
            default logging.getLogger(name)

    Returns:
        logging.LoggerAdapter: an adapter to the logger object with the
            given name. The adapter adds environment information that is
            available to the formatter.

    """
    try:
        return _logger_cache[name]
    except Exception:
        pass

    logger = logging.getLogger(LOGGER_NAME + "." + name)

    # Base Loggers will always have a null handler in order to
    # avoid stray warning messages.
    logger.addHandler(logging.NullHandler())

    # Base Loggers always pass their messages to the base logger.  All
    # severity filtering is done at the handler level.
    logger.setLevel(logging.DEBUG)

    logger_adapter = BaseLoggerAdapter(logger)
    _logger_cache[name] = logger_adapter
    return logger_adapter


class Severity(object):
    """Mapping between this class and the levels in the logging module.

    This is strictly a convenience class.
    """
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


class Interval(enum.Enum):
    """Time interval options for rotating file handlers

    Example:
        >>> add_file_handling(rotate_every=Interval.DAY)

    """
    NEVER = 0
    HOUR = 1
    DAY = 2
    WEEK = 3
    MONTH = 4
    SUNDAY = 5
    MONDAY = 6
    TUESDAY = 7
    WEDNESDAY = 8
    THURSDAY = 9
    FRIDAY = 10
    SATURDAY = 11
    MIDNIGHT = 12


#: (dict) Maps between a standard interval and args for the logging module
_interval_map = {
    Interval.HOUR: ("H", 1),
    Interval.DAY: ("D", 1),
    Interval.WEEK: ("D", 7),
    Interval.MONTH: ("D", 30),
    Interval.MONDAY: ("W0", 1),
    Interval.TUESDAY: ("W1", 1),
    Interval.WEDNESDAY: ("W2", 1),
    Interval.THURSDAY: ("W3", 1),
    Interval.FRIDAY: ("W4", 1),
    Interval.SATURDAY: ("W5", 1),
    Interval.SUNDAY: ("W6", 1),
    Interval.MIDNIGHT: ("midnight", 1)
}


# LOG FORMATTING

def log_formatter(date=False, name=False, path=False, module=False,
                  line=False, function=False, severity=False, time=False,
                  seconds=False, milliseconds=False):
    """Creates a standardized logging.Formatter

    Most of the attributes of LogRecords are supported, as well as custom
    data supported via the BaseLoggingAdapter.

    Args:
        date (bool): Include the day of the logging call

        name (bool): Include the name of the logger.

        path (bool): Include the path to the calling module.

        module (bool): Include the name of the calling module; this
            argument is ignored if path is True.

        line (bool): Include the line number on which the calling code
            occurs. This argument is ignored if path and module are both
            False.

        function (bool): Include the name of the calling function or
            method.

        severity (bool): Include the level name (debug, info, warning,
            etc.)

        time (bool): Include the time to the minute of the logging call.

        seconds (bool): Include the seconds in the timestamp.

        milliseconds (bool): Include a dot-separated millisecond value after
            the seconds in the timestamp

    Returns:
        LogFormatter: A formatter initialized with a constructed
            printf-style string based on the arguments passed into this
            function.

    """

    # The process here takes advantage of a python quirk:  Multiplying any
    # string by 0 returns an empty string. This makes for a pretty clean
    # way to build complex strings with lots of optional arguments.
    fmt_str = (
        ("%(asctime)s | " * (date or time))
        + ("%(levelname)s | " * severity)
        + ("%(name)s | " * name)
        + ("%(pathname)s | " * (path and not line and not module))
        + ("%(pathname)s, line %(lineno)d | " * (path and line and not module))
        + ("%(module)s | " * (module and not path and not line))
        + ("%(module)s, line %(lineno)d | " * (module and not path and line))
        + ("%(funcName)s() | " * function)
        + ("%(message)s")
    )

    strfmt_str = (
        ("%b %d %Y" * date)
        + (" %I:%M" * (time))
        + (":%S" * (time and seconds))
        + (".%f" * (time and milliseconds))
        + (" %p" * time)
    )

    return LogFormatter(fmt_str, strfmt_str)


class LogFormatter(logging.Formatter):
    """Formatter with a wider range of datefmt options.

    Adds support for "%f" for microseconds.
    """
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            datefmt = datefmt.replace("%f", str(int(record.msecs)).zfill(3))
            return time.strftime(datefmt, ct)
        else:
            return time.strftime("%Y-%m-%d %H:%M:%S", ct)


class Formatters(enum.Enum):
    """Enumerates available standard formatters.

    Typical usage example:
        lumberjack.add_console_output(lumberjack.Formatters.BASIC)
    """
    BASIC = 1
    DATED = 2
    DETAIL = 3
    TIMESTAMP = 4


def basic_formatter():
    """Builds a simple formatter with just the severity and the message."""
    return log_formatter(severity=True)


def dated_formatter():
    """Builds a formatter with date, time, severity, and message"""
    return log_formatter(date=True, time=True, seconds=True, severity=True)


def timestamp_formatter():
    """Builds a formatter with a detailed timestamp, severity, and message."""
    return log_formatter(date=True, time=True, seconds=True, severity=True,
                            milliseconds=True)


def detail_formatter():
    """Builds a formatter with information both about the log event and the
    originating scope"""
    return log_formatter(date=True, severity=True,
                            module=True, line=True, function=True, time=True,
                            seconds=True, milliseconds=True)


_formatter_map = \
    {Formatters.BASIC: basic_formatter,
     Formatters.DATED: dated_formatter,
     Formatters.DETAIL: detail_formatter,
     Formatters.TIMESTAMP: timestamp_formatter,
     }


# FILTERING

class StackFilter(logging.Filter):
    """A custom filter attached to every handler created in this module.

    This filter checks two things: the traced stack of the log call, and the
    logging severity level.

    StackFilters are created when calling the add_*_output() functions.
    """

    def __init__(self):
        self.module_stack = _enclosing_modules()
        self.module_stack_key = tuple(_unique_in_order(self.module_stack))
        self.init_stack = {mod for mod in self.module_stack if not mod.startswith("importlib.")}

        # The first time a handler is created for this particular dependency
        # chain, we need to set a default severity level
        _level_filters.setdefault(
            self.module_stack_key, (self.init_stack, DEFAULT_LOG_LEVEL)
        )

        super(StackFilter, self).__init__()

    def filter(self, record):
        # if the LogRecord has not gone through a StackFilter before, we
        # grab the dependency hierarchy and attach it to the record for
        # efficiency
        try:
            calling_stack = record.calling_stack
        except AttributeError:
            calling_stack = set(_enclosing_modules())
            record.calling_stack = calling_stack

        # This is where the magic happens!
        # If the record did not originate in the same dependency stack as
        # this filter, we reject it.
        if not self.init_stack.issubset(calling_stack):
            return False

        # We also check the severity level set for this dependency stack.
        for mod_stack, level in _level_filters.values():
            if mod_stack.issubset(calling_stack):
                filter_level = level
                break
        else:
            filter_level = None

        # No filter level was set... better to err on the side of caution
        if not filter_level:
            return True

        if record.levelno >= filter_level:
            return True

        return False


def set_severity(level):
    """Set the severity level for the Base Logger with respect to the
    current dependency stack.

    This function should be called at the top level of your application.

    Args:
        level (int): A logging level as set in lumberjack.Severity

    Typical usage:
        import lumberjack
        logger = lumberjack.get_logger(__name__)
        lumberjack.set_severity(lumberjack.Severity.INFO)
    """
    modules = _enclosing_modules_unique()
    _level_filters[tuple(modules)] = set(modules), level


# HANDLERS

DAYLIGHT_SAVINGS_OFFSET = 3600


class BasicFileLogHandler(logging.handlers.TimedRotatingFileHandler):

    rotated_file_format = "{base}.{timestamp}{ext}"

    def doRollover(self):
        """Overridden from logging.handlers.TimedRotatingFileHandler."""

        # Most of the following code is copied directly from logging.handlers,
        # with easier-to-read variable names and a new formatting scheme for
        # logs that are rotated.

        self.close_stream()

        # get the time that this sequence started
        current_time = int(time.time())
        daylight_savings_time_now = time.localtime(current_time)[-1]
        rollover_time = self.rolloverAt - self.interval
        rollover_time_tuple = time.localtime(rollover_time)

        # account for daylight savings time between now and when the log file
        # was created
        daylight_savings_time_then = rollover_time_tuple[-1]
        if daylight_savings_time_now != daylight_savings_time_then:
            if daylight_savings_time_now:
                offset = DAYLIGHT_SAVINGS_OFFSET
            else:
                offset = -DAYLIGHT_SAVINGS_OFFSET
            rollover_time_tuple = time.localtime(rollover_time + offset)

        # Obtain the name for the newly-rotated file
        base_file_name, extension = os.path.splitext(self.baseFilename)
        rotated_filename = self.rotated_file_format.format(
            base=base_file_name,
            timestamp=time.strftime(self.suffix, rollover_time_tuple),
            ext=extension
        )

        if os.path.exists(rotated_filename):
            os.remove(rotated_filename)

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, rotated_filename)

        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

        self.stream = self._open()

        new_rollover_time = self.computeRollover(current_time)
        while new_rollover_time <= current_time:
            new_rollover_time = new_rollover_time + self.interval

        # Adjust for changes in Daylight Savings Time between now and the next
        # rotation interval, if the interval is at Midnight or a specific day
        # of the week.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')):
            daylight_savings_time_next = time.localtime(new_rollover_time)[-1]
            if daylight_savings_time_now != daylight_savings_time_next:

                # DST kicks in before next rollover, so we need to deduct
                if not daylight_savings_time_now:
                    offset = -DAYLIGHT_SAVINGS_OFFSET

                # DST bows out before next rollover, so we need to add
                else:
                    offset = DAYLIGHT_SAVINGS_OFFSET

                new_rollover_time += offset

        self.rolloverAt = new_rollover_time

    def getFilesToDelete(self):
        """Overridden from logging.handlers.TimedRotatingFileHandler"""
        if self.backupCount == 0:
            return []
        base_file_name, extension = os.path.splitext(self.baseFilename)
        expand_file_name = self.rotated_file_format.format(
            base=base_file_name, timestamp="*", ext=extension
        )
        backups = glob.glob(expand_file_name)
        n_backups = len(backups)
        if n_backups > self.backupCount:
            backups.sort()
            return backups[:(n_backups - self.backupCount)]
        else:
            return []

    def close_stream(self):
        if self.stream:
            self.stream.close()
            self.stream = None


def add_handler(handler):
    """Adds a handler to the Base Logger."""
    base_logger = get_base_logger()
    handler.addFilter(StackFilter())
    base_logger.addHandler(handler)
    return handler


def _configure_and_add_handler(handler, severity, formatter):

    # supply a default formatter if none is provided
    if formatter is None:
        formatter = dated_formatter()

    # add a standardized formatter
    elif isinstance(formatter, enum.Enum):
        formatter = _formatter_map[formatter]()

    # if neither is true, formatter is assumed to be a Formatter instance

    handler.setLevel(severity)
    handler.setFormatter(formatter)
    add_handler(handler)


def add_console_output(severity=logging.NOTSET, formatter=None, stream=None):
    """Add a console-output handler to the Base Logger.

    This handler is only valid for the current dependency stack.

    Args:
        severity (int): One of the standard logging severity levels.

        formatter (logging.Formatter, enum.Enum or None): Can be either a
            regular Formatter, an enum pointing to one of our standard
            formatters, or None.  If formatter is None, a default will be
            applied.

    Returns:
        logging.Handler: A logging handler object with a StackFilter
    """
    handler = logging.StreamHandler(stream=stream)
    _configure_and_add_handler(handler, severity, formatter)
    return handler


def add_file_output(filename, severity=logging.NOTSET, formatter=None,
                    rotate_every=Interval.NEVER, backup_count=0, encoding=None):
    """Add a file-output handler to the Base Logger.

    This handler is only valid for the current dependency stack.

    Args:
        filename (str): a path to a log file

        severity (int): One of the standard logging severity levels.

        formatter (logging.Formatter, enum.Enum or None): Can be either a
            regular Formatter, an enum pointing to one of our standard
            formatters, or None.  If formatter is None, a default will be
            applied.

        rotate_every (enum.Enum): One of the enumerated rotation intervals, if
            a rotating file handler is desired.  If no interval is provided,
            a standard handler will be used.

        backup_count (int): The number of log files to keep when using a
            rotating file handler.  If backup_count is zero, no backup files
            will be removed.  This argument is only valid if rotate_every is
            also provided.

    Returns:
        logging.Handler: A logging handler object with a StackFilter

    Example:
        >>> # a rotating file handler is used here, that resets every Sunday
        >>> add_file_output(rotate_every=Interval.MONDAY)
    """
    if rotate_every == Interval.NEVER:
        handler = FileHandler(filename, encoding=encoding)
    else:
        when, interval = _interval_map[rotate_every]
        handler = BasicFileLogHandler(
            filename,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
        )
    _configure_and_add_handler(handler, severity, formatter)
    return handler


def add_exception_handling():
    raise NotImplementedError("just a placeholder for now!")


def get_all_base_handlers():
    """Returns a list of all the handlers in the base logger"""
    return get_base_logger().handlers


def get_valid_base_handlers():
    """Returns a list of valid handlers for the current execution stack."""
    calling_stack = set(_enclosing_modules())
    handlers = get_base_logger().handlers
    valid_handlers = list()
    for handler in handlers:
        filter_ = _get_stack_filter(handler)
        if filter_ and filter_.init_stack.issubset(calling_stack):
            valid_handlers.append(handler)
        elif not filter_:
            valid_handlers.append(handler)
    return valid_handlers


@contextmanager
def suppress_root_handlers():
    """CONTEXT MANAGER: Temporarily suppress all root-level handlers.

    The handlers are restored when the context exits.
    """
    handlers = logging.root.handlers
    logging.root.handlers = [logging.NullHandler()]
    yield
    logging.root.handlers = handlers


# UTILITIES

def _enclosing_modules():
    """Returns a list of the names of every enclosing module in the
    dependency stack. This list can have duplicate entries."""
    return inspections.get_mod_trace(inspect.currentframe())


def _enclosing_modules_unique():
    """Returns a list of unique names of every enclosing module in the
    dependency stack."""
    return _unique_in_order(_enclosing_modules())


def _get_stack_filter(handler):
    """Returns the stack filter for the given handler (if any)"""
    for filter_ in handler.filters:
        if isinstance(filter_, StackFilter):
            return filter_


def _unique_in_order(sequence):
    """Uniquifies a sequence while preserving order.

    Args:
        sequence: any iterable of items that you want to uniquify.  The
            iterable will not be mutated, but bear in mind that it will be
            iterated over, so generators might be exhausted.

    Returns: list

    """
    visited = set()
    result = list()
    for item in sequence:
        if item in visited:
            continue
        visited.add(item)
        result.append(item)
    return result

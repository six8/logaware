import inspect
import sys
import logging
from six import with_metaclass, python_2_unicode_compatible, text_type


class LogFormatException(Exception):
    """
    Exception raised if there is an error processing the
    substitution format of a message.
    """
    def __init__(self, message, original):
        super(LogFormatException, self).__init__(message)
        self.original = original


@python_2_unicode_compatible
class LogLevel(object):
    """
    A logging level

    Args:
        level (int): Log level
        name (unicode): Level name
        traceback (bool): Include traceback when logging
    """
    def __init__(self, level, name, traceback=False):
        self.level = level
        self.name = name
        self.traceback = traceback

    def __repr__(self):
        return '<LogLevel %s (%s)>' % (self.name, self.level)

    def __int__(self):
        return self.level

    def __str__(self):
        return self.name


def log_method_factory(name, level, traceback=False):
    """
    Create a method that will log at the specified level

    Args:
        name (bytes): Method name
        level (LogLevel): Logging level
        traceback (bool): Include traceback when logging
    """
    level = int(level)
    if traceback:
        def log_method(self, *args, **kwargs):
            # Include traceback by default
            kwargs.setdefault('exc_info', 1)
            return self._log(level, *args, kwargs=kwargs)
    else:
        def log_method(self, *args, **kwargs):
            return self._log(level, *args, kwargs=kwargs)

    log_method.__name__ = name
    return log_method


class LoggerMetaClass(type):
    """
    Metaclass that sets up log levels
    """
    def __new__(mcs, name, bases, attrs):
        levels = {}
        # Inherit base class levels
        for base in bases:
            base_levels = getattr(base, '_log_levels', None)
            if base_levels:
                levels.update(base_levels)

        for key, val in attrs.items():
            if isinstance(val, LogLevel):
                levels[val.level] = val

        attrs['_log_levels'] = levels

        return super(LoggerMetaClass, mcs).__new__(mcs, name, bases, attrs)


class AwareLogger(with_metaclass(LoggerMetaClass)):
    """
    Similar to a :class:`logging.Logger` but is context aware. There
    is only one ``ContextLogger`` per context and it automatically
    figures out the module that is being logged from. Other
    information about the context can also be injected into the log
    message.

    The ``ContextLogger`` will use :func:`logging.getLogger` to get a
    Logger based on which module the logger is being called from. For
    example, if this was being called in ``logaware.logger``, the log
    message would include ``logaware.logger`` as the logger name::

        >>> import logging
        >>> logging.getLogger().setLevel(logging.DEBUG)
        >>> log = AwareLogger()
        >>> log.info('Test message').module
        '...logaware.logger'
    """

    # Store level names on this object. This allows levels and names
    # to be added without polluting the global logger.
    #: CRITICAL Log level
    CRITICAL = LogLevel(logging.CRITICAL, 'CRITICAL')
    FATAL = CRITICAL
    ERROR = LogLevel(logging.ERROR, 'ERROR')
    WARNING = LogLevel(logging.WARNING, 'WARNING')
    WARN = WARNING
    INFO = LogLevel(logging.INFO, 'INFO')
    DEBUG = LogLevel(logging.DEBUG, 'DEBUG')

    #: Log ERROR level message. See :func:`AwareLogger.log` for argument info.
    error = log_method_factory('error', ERROR)

    #: Log ERROR level message with traceback. See :func:`AwareLogger.log` for argument info.
    exception = log_method_factory('exception', ERROR, traceback=True)

    #: Log CRITICAL level message. See :func:`AwareLogger.log` for argument info.
    critical = log_method_factory('critical', CRITICAL)
    #: Alias for :func:`AwareLogger.critical`
    fatal = critical

    #: Log DEBUG level message. See :func:`AwareLogger.log` for argument info.
    debug = log_method_factory('debug', DEBUG)

    #: Log INFO level message. See :func:`AwareLogger.log` for argument info.
    info = log_method_factory('info', INFO)

    #: Log WARNING level message. See :func:`AwareLogger.log` for argument info.
    warning = log_method_factory('warning', WARNING)
    #: Alias for :func:`AwareLogger.warning`
    warn = warning

    def log(self, level, msg, **kwargs):
        """
        Log a message at specified ``level``

        Args:
            level (int): Logging level
            msg (unicode): Log message
            **kwargs: Extra logging parameters and substitution
                parameters for log message.

        Returns:
            logging.LogRecord: LogRecord sent to logging handler
        """
        return self._log(level, msg, kwargs)

    def get_level_name(self, level):
        """
        Get the textual representation of logging ``level``.

        Args:
            level (int): Logging level

        Returns:
            unicode: Name of logging level
        """
        return text_type(self._log_levels.get(level, (u'Level %s' % level)))

    def isEnabledFor(self, level):
        """
        Is this logger enabled for level 'level'?

        Note: Wrapper around native logger method.

        Args:
            level (int): Logging level

        Returns:
            boolean: Whether or not logging is enabled for `level`.
        """
        # _get_caller will only work if the callstack is exactly 3
        module_name, filename, line_number, func_name = _get_caller()
        logger = logging.getLogger(module_name)
        return logger.isEnabledFor(level)

    def _log(self, level, message, kwargs):
        # _get_caller will only work if the callstack is exactly 3
        module_name, filename, line_number, func_name = _get_caller()
        logger = logging.getLogger(module_name)
        if logger.isEnabledFor(level):
            exc_info = kwargs.pop('exc_info', 0)
            message = self._format_message(message, kwargs)
            extra = self._get_extra(message, kwargs)

            if exc_info:
                # Include exception in log output
                if not isinstance(exc_info, tuple):
                    exc_info = sys.exc_info()

                if exc_info == (None, None, None):
                    # There's no exception. Python 3.3 and 3.4
                    # choke on the ``None`` triple.
                    exc_info = None

            record = logger.makeRecord(
                logger.name,
                level,
                filename,
                line_number,
                message,
                args=None,
                exc_info=exc_info,
                func=func_name,
                extra=extra
            )
            # Override level name in case it is a custom level added
            # to this instance.
            record.levelname = self.get_level_name(level)

            logger.handle(record)
            return record

    def _get_extra(self, message, kwargs):
        """
        Process extra data for record
        """
        kwargs = {
            # Exclude empty values
            k: v for k, v in kwargs.items() if v not in (None, '')
        }
        if kwargs:
            return {
                'data': kwargs
            }
        else:
            return {}

    def _format_message(self, message, kwargs):
        if not kwargs:
            return message

        # Use string.format to format log messages instead
        # of % style formatting.
        try:
            return message.format(**kwargs)
        except Exception as e:
            raise LogFormatException(
                u'Error formatting log message {message} with keyword '
                u'args {kwargs}: {error_class} -- {error}'.format(
                    message=message,
                    kwargs=kwargs,
                    error_class=e.__class__.__name__,
                    error=e
                ),
                original=e
            )


def _get_caller():
    """
    Returns information about the calling stack.

    The callstack must be exactly 3 deep for this to work. Typically
    this includes a logging function, :func:`AwareLogger._log` and
    this function.

    Returns:
        tuple: (module_name, filename, line_number, func_name)
    """
    caller_frame, module = None, None
    try:
        # Inspecting the call stack may seem expensive,
        # but this is more or less what the
        # logging module does already.
        caller_frame = logging.currentframe()
        caller_frame = caller_frame.f_back
        module = inspect.getmodule(caller_frame)
        co = caller_frame.f_code

        return (
            module.__name__ if module else None,
            co.co_filename,
            caller_frame.f_lineno,
            co.co_name
        )
    finally:
        # Prevent stack frames from causing memory leaks
        del caller_frame
        del module

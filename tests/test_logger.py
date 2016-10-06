import inspect
import logging
import pytest
from six import text_type
from logaware.logger import AwareLogger, LogFormatException, LogLevel, log_method_factory
from .example import submodule


def _lineno():
    """
    Returns the current line number where this is called from
    """
    return inspect.currentframe().f_back.f_lineno


def some_function(log):
    """
    Logs a message and returns the line number that the log message
    is on.
    """
    log.warn('Logging from within some_function')
    return _lineno() - 1


def test_local_context(lastlog):
    """
    Verify context logger gets correct module names, line numbers,
    and functions
    """
    log = AwareLogger()
    log.debug('test')
    assert lastlog() == \
        bytes(('tests.test_logger:DEBUG:test:%s:%d:test_local_context' % (
            __file__, _lineno() - 1)).encode('utf8'))


def test_function_context(lastlog):
    """
    Verify context logger gets correct module names, line numbers,
    and functions when called from a function
    """
    log = AwareLogger()
    line = some_function(log)
    assert lastlog() ==\
        bytes(('tests.test_logger:WARNING:Logging from within some_function:%s:%d:some_function' % (
            __file__,
            line)).encode('utf8'))


def test_submodule_class_context(lastlog):
    """
    Verify context logger gets correct module names, line numbers,
    and functions when called from a class instance
    """
    log = AwareLogger()
    line = submodule.Tester(log).run()
    assert lastlog() == \
        bytes(('tests.example.submodule:INFO:Logging from within Tester.run:%s:%d:run' % (
            submodule.__file__.replace('.pyc', '.py'),
            line)).encode('utf8'))


def test_submodule_function_context(lastlog):
    """
    Verify context logger gets correct module names, line numbers,
    and functions when called from a sub-module function
    """
    log = AwareLogger()
    line = submodule.module_function(log)
    assert lastlog() == \
        bytes(('tests.example.submodule:DEBUG:Logging from within module_function:%s:%d:module_function' % (
            submodule.__file__.replace('.pyc', '.py'),
            line)).encode('utf8'))


@pytest.mark.parametrize('method, level, exc_info', [
    ('debug', logging.DEBUG, 0),
    ('debug', logging.DEBUG, 1),
    ('warn', logging.WARNING, 0),
    ('warn', logging.WARNING, 1),
    ('warning', logging.WARNING, 0),
    ('error', logging.ERROR, 0),
    ('error', logging.ERROR, 1),
    ('critical', logging.CRITICAL, 0),
    ('critical', logging.CRITICAL, 1),
    ('fatal', logging.CRITICAL, 0),
    ('info', logging.INFO, 0),
    ('info', logging.INFO, 1),
    ('exception', logging.ERROR, 0),
    ('exception', logging.ERROR, 1),
])
def test_logging_levels(method, level, exc_info, lastlog):
    """
    Verify logger logs the correct logging levels
    """
    level_name = logging.getLevelName(level)

    log = AwareLogger()
    log_method = getattr(log, method)

    try:
        # Raise some exception so we can test exc_info
        raise TypeError('Test exc_info')
    except TypeError:
        log_method('test', exc_info=exc_info)
        expected_log = bytes(
            'tests.test_logger:{level_name}:test:{filename}:{lineno}:test_logging_levels'.format(
                level_name=level_name, filename=__file__, lineno=_lineno() - 3).encode('utf8')
        )
        lines = lastlog().split(b'\n')
        assert lines[0] == expected_log, \
            'First log line should be expected log message'

        if exc_info:
            # Must be exc_info
            assert len(lines) > 1
            assert lines[1].startswith(b'Traceback'), \
                'Expected traceback info in log message'


@pytest.mark.parametrize('level, exc_info', [
    (logging.DEBUG, 0),
    (logging.DEBUG, 1),
    (logging.WARNING, 0),
    (logging.WARNING, 1),
    (logging.ERROR, 0),
    (logging.ERROR, 1),
    (logging.CRITICAL, 0),
    (logging.CRITICAL, 1),
    (logging.INFO, 0),
    (logging.INFO, 1),
])
def test_log_method(level, exc_info, lastlog):
    """
    Verify logger level messages log correctly
    """
    level_name = logging.getLevelName(level)

    log = AwareLogger()

    try:
        # Raise some exception so we can test exc_info
        raise ValueError('Test exc_info')
    except ValueError:
        log.log(level, 'test', exc_info=exc_info)
        expected_log = bytes(
            'tests.test_logger:{level_name}:test:{filename}:{lineno}:test_log_method'.format(
                level_name=level_name, filename=__file__, lineno=_lineno() - 3).encode('utf8')
        )
        lines = lastlog().split(b'\n')
        assert lines[0] == expected_log, \
            'First log line should be expected log message'

        if exc_info:
            # Must be exc_info
            assert len(lines) > 1
            assert lines[1].startswith(b'Traceback'), \
                'Expected traceback info in log message'


def test_exc_info(lastlog):
    """
    Verify logger includes traceback information when `exc_info`
    is provided.
    """
    log = AwareLogger()

    exc_info = (IndexError, IndexError('test'), None)
    log.debug('test', exc_info=exc_info)
    expected_log = bytes(('tests.test_logger:DEBUG:test:%s:%d:test_exc_info' % (
        __file__, _lineno() - 2)).encode('utf8'))
    lines = lastlog().split(b'\n')
    assert lines[0] == expected_log, \
        'First log line should be expected log message'

    # Our exception in exc_info should have been logged
    assert len(lines) == 2
    assert lines[1] == b'IndexError: test'


@pytest.mark.parametrize('message, kwargs, expected_message', [
    ('args {foo} {bar}', {'foo': 1, 'bar': 2}, b'args 1 2'),
    ('args {foo}', {'foo': 'a', 'bar': 2}, b'args a'),
    ('args {foo:d}', {'foo': 1}, b'args 1'),
])
def test_log_formatting(message, kwargs, expected_message, lastlog):
    """
    Verify variable interpolation in log messages
    """
    log = AwareLogger()

    for method in (
        'debug',
        'warn',
        'warning',
        'error',
        'critical',
        'fatal',
        'info',
        'exception',
    ):
        log_method = getattr(log, method)
        log_record = log_method(message, **kwargs)

        for k, v in kwargs.items():
            # kwargs are also added as 'extra' for log records
            assert log_record.data[k] == v

        logged = lastlog()
        assert logged
        logged_message = logged.split(b':')[2]
        assert logged_message == expected_message


@pytest.mark.parametrize('message, kwargs, error_type', [
    ('Some args {0}', {'foo': 'a'}, IndexError),
    ('Some args {foo} {bar}', {'foo': 'a'}, KeyError),
    ('Some args {foo:d}', {'foo': 'a'}, ValueError),
])
def test_log_formatting_error(message, kwargs, error_type):
    """
    Verify variable interpolation failures happen immediately when
    logged, not at the time the message hits a handler.
    """
    log = AwareLogger()
    log_method = getattr(log, 'debug')

    try:
        log_method(message, **kwargs)
    except LogFormatException as e:
        assert type(e.original) is error_type
    else:
        pytest.fail('Expected LogFormatException')


def test_log_level_min(lastlog):
    """
    Verify messages can be excluded by log level
    """
    logger = logging.getLogger('tests')
    logger.setLevel(999)

    log = AwareLogger()
    log.debug('Will not be logged')
    assert lastlog() == b''


def test_log_level():
    """
    Verify LogLevel basics
    """
    level = LogLevel(10, 'TEN')
    assert text_type(level.name) == 'TEN'
    assert int(level) == 10
    assert repr(level) == '<LogLevel TEN (10)>'


def test_custom_level(lastlog):
    """
    Verify that additional custom level can be added
    """
    class CustomLogger(AwareLogger):
        BLERG = LogLevel(42, 'BLERG')
        blerg = log_method_factory('blerg', BLERG)

    log = CustomLogger()

    # Verify base levels are inherited
    assert log.get_level_name(20) == 'INFO'
    # Verify custom levels
    assert log.get_level_name(42) == 'BLERG'

    log.blerg('Blergit!')
    expected_log = bytes(
        'tests.test_logger:BLERG:Blergit!:{filename}:{lineno}:test_custom_level'.format(
            filename=__file__, lineno=_lineno() - 3).encode('utf8')
    )
    assert lastlog() == expected_log


def test_custom_level_with_traceback(lastlog):
    """
    Verify that additional custom levels with tracebacks can be added
    """
    class CustomLogger(AwareLogger):
        OOPS = LogLevel(43, 'OOPS')
        oops = log_method_factory('oops', OOPS, traceback=True)

    log = CustomLogger()

    assert log.get_level_name(43) == 'OOPS'

    try:
        # Raise some exception so we can test exc_info
        raise ValueError('Test exc_info')
    except ValueError:
        log.oops('Oooops!')
        expected_log = bytes(
            'tests.test_logger:OOPS:Oooops!:{filename}:{lineno}:test_custom_level_with_traceback'.format(
                filename=__file__, lineno=_lineno() - 3).encode('utf8')
        )
        lines = lastlog().split(b'\n')
        assert lines[0] == expected_log, \
            'First log line should be expected log message'

        # Must be exc_info
        assert len(lines) > 1
        assert lines[1].startswith(b'Traceback'), \
            'Expected traceback info in log message'

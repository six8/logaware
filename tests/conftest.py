import logging
import pytest
from io import BytesIO, TextIOWrapper


@pytest.fixture
def lastlog_factory(request):
    """
    Returns a function that each time called returns the last
    line to be logged to the 'tests' logger.
    """
    def _lastlog_factory(
            logger,
            format=u'%(name)s:%(levelname)s:%(message)s:%(pathname)s:%(lineno)s:%(funcName)s',
            encoding='utf8'):

        raw_stream = BytesIO()
        stream = TextIOWrapper(raw_stream, encoding=encoding)

        logger = logging.getLogger(logger)
        logger.setLevel(1)
        handler = logging.StreamHandler(stream)
        handler.setLevel(logger.level)
        handler.setFormatter(logging.Formatter(format))
        logger.addHandler(handler)

        # Make sure our logger is not disabled.
        disabled, logger.disabled = logger.disabled, 0

        def finish():
            logger.removeHandler(handler)

        request.addfinalizer(finish)

        def log_pop():
            handler.flush()
            raw_stream.seek(0)
            data = raw_stream.read().strip()
            raw_stream.truncate(0)
            raw_stream.seek(0)
            return data

        return log_pop

    return _lastlog_factory


@pytest.fixture
def lastlog(lastlog_factory):
    """
    Returns a function that each time called returns the last
    line to be logged to the 'tests' logger.
    """
    return lastlog_factory('tests')

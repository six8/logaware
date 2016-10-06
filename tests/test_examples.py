from .example.loggers import log, custom_log, log_meta_context, meta_log


def test_example_basic_logger(lastlog_factory):
    """
    Verify basic shared logger is context aware.
    """
    lastlog = lastlog_factory('tests', format=u'%(name)s:%(levelname)s:%(message)s')

    log.info('{user} logged in.', user='admin')

    log_message = lastlog()
    assert log_message.startswith(b'tests.test_examples:'), \
        'Expect module to be test\'s module, not loggers module.'
    assert log_message == b'tests.test_examples:INFO:admin logged in.'


def test_example_custom_logger(lastlog_factory):
    """
    Verify custom logger has custom logging level methods.
    """
    lastlog = lastlog_factory('tests', format=u'%(name)s:%(levelname)s:%(message)s')

    custom_log.info('{user} logged in.', user='admin')

    expected_log = b'tests.test_examples:INFO:admin logged in.'
    assert lastlog() == expected_log

    custom_log.audit(
        '{user} changed {key} from {old_value} to {new_value}',
        user='admin',
        key='security_enabled',
        old_value=True,
        new_value=False
    )

    expected_log = b'tests.test_examples:AUDIT:admin changed security_enabled from True to False'
    assert lastlog() == expected_log

    try:
        # Raise some exception so we can test exc_info
        raise ValueError('Test exc_info')
    except ValueError:
        custom_log.fail('{user} failed.', user='admin')

    expected_log = b'tests.test_examples:FAIL:admin failed.'

    lines = lastlog().split(b'\n')
    assert lines[0] == expected_log, \
        'First log line should be expected log message'

    # Must be exc_info
    assert len(lines) > 1
    assert lines[1].startswith(b'Traceback'), \
        'Expected traceback info in log message'


def test_example_meta_logger(lastlog_factory):
    """
    Verify example meta logger can get meta info from thread context.
    """
    lastlog = lastlog_factory('tests', format=u'%(name)s:%(levelname)s:%(message)s:%(meta)s')

    # Not in meta context so no meta data.
    meta_log.error('User not found.')
    assert lastlog() == b'tests.test_examples:ERROR:User not found.:{}'

    with log_meta_context(user='admin'):
        # Log message will have ``user`` from meta context
        meta_log.info('User logged in.')

        assert lastlog() == b'tests.test_examples:INFO:User logged in.:{"user":"admin"}'

        with log_meta_context(name='Bob'):
            # Log message will have ``user`` from parent meta context
            # and ``name`` from current context.
            meta_log.info('User updated info.')

            assert lastlog() == b'tests.test_examples:INFO:User updated info.:{"name":"Bob", "user":"admin"}'

        # Log message will have only have meta from original context
        meta_log.info('User says hi.')

        assert lastlog() == b'tests.test_examples:INFO:User says hi.:{"user":"admin"}'

    # {user} will be None because the meta context has exited
    meta_log.info('User logged out.')

    assert lastlog() == b'tests.test_examples:INFO:User logged out.:{}'

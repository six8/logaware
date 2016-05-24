# coding=utf-8
from six import text_type
from logaware.metalogger import MetaAwareLogger, LogMetaManager, LogMeta
import pytest


@pytest.mark.parametrize(
    ['encoding', 'message', 'metadata', 'bytes_message', 'unicode_message'],
    [
        (
            'latin1',
            'User {user} ({id}) logged in',
            dict(user='bob', id=20),
            b'tests.test_meta_logger:User bob (20) logged in:{"id":20, "user":"bob"}',
            u'tests.test_meta_logger:User bob (20) logged in:{"id":20, "user":"bob"}',
        ),
        (
            'utf8',
            u'User {user} logged in',
            dict(user=u'fӫӫ', id=1),
            b'tests.test_meta_logger:User f\xd3\xab\xd3\xab logged in:{"id":1, "user":"f\xd3\xab\xd3\xab"}',
            u'tests.test_meta_logger:User fӫӫ logged in:{"id":1, "user":"fӫӫ"}',
        ),
    ]
)
def test_log_meta_json(
        encoding, message, metadata, bytes_message, unicode_message, lastlog_factory):
    """
    Verify that log meta data can be logged in JSON format
    """
    lastlog = lastlog_factory(
        'tests',
        format=u'%(name)s:%(message)s:%(meta)s',
        encoding=encoding)

    meta = LogMetaManager()
    meta.set_meta(**metadata)

    log = MetaAwareLogger(lambda: meta.get_meta())

    log_record = log.info(message, **metadata)
    assert log_record.meta == metadata
    assert log_record.message == message.format(**metadata)

    logged = lastlog()
    assert logged == bytes_message

    decoded = logged.decode(encoding)
    assert decoded == unicode_message


def test_log_meta_invalid_json():
    """
    Verify that setting non-JSONifiable meta will raise TypeError
    """
    meta = LogMetaManager()

    with pytest.raises(TypeError):
        meta.set_meta(user=NotImplemented)


def test_log_meta_manager_update():
    """
    Verify LogMeta can be updated through LogMetaManager
    """
    meta = LogMetaManager()
    meta.set_meta(user='foo')

    assert meta.get_meta() == {'user': 'foo'}

    meta.set_meta(user='bob', id=1)

    assert meta.get_meta() == {'user': 'bob', 'id': 1}


def test_log_meta_update():
    """
    Verify LogMeta can not be updated
    """
    meta = LogMeta(user='foo')

    assert meta['user'] == 'foo'

    with pytest.raises(TypeError):
        meta['user'] = 'bob'

    with pytest.raises(AttributeError):
        # Update should not exist
        meta.update({'user': 'bob'})


@pytest.mark.parametrize(
    ['meta', 'json_str', 'json_unicode'],
    [
        (
            {'user': 'bob', 'version': 1.1, 'empty': None},
            b'{"user":"bob", "version":1.1}',
            u'{"user":"bob", "version":1.1}',
        ),
        (
            {'name': u'bŌŌk', 'count': 100},
            b'{"count":100, "name":"b\xc5\x8c\xc5\x8ck"}',
            u'{"count":100, "name":"bŌŌk"}',
        ),
    ]
)
def test_log_meta_json(meta, json_str, json_unicode):
    """
    Verify LogMeta JSONifies to bytes and unicode
    """
    meta = LogMeta(**meta)

    assert bytes(meta) == json_str
    # Specifically check __bytes__ because Python 2 just calls
    # __str__ for ``bytes()``
    assert meta.__bytes__() == json_str
    assert text_type(meta) == json_unicode

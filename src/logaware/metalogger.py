from collections import Mapping
from copy import deepcopy
from six import python_2_unicode_compatible
from .logger import AwareLogger


try:
    from simplejson import json
except:
    import json


class MetaAwareLogger(AwareLogger):
    """
    Similar to a :class:`AwareLogger` and also track additional
    metadata.

    Args:
        getter (callable): Callable to get the current LogMeta.
            It's up to the framework to decide how meta is
            obtained.
    """
    def __init__(self, getter):
        super(MetaAwareLogger, self).__init__()
        self._meta_getter = getter

    def _get_extra(self, message, kwargs):
        """
        Inject LogMeta into LogRecord extra
        """
        extra = super(MetaAwareLogger, self)._get_extra(message, kwargs)
        meta = self._meta_getter()
        extra['meta'] = meta
        return extra


@python_2_unicode_compatible
class LogMeta(Mapping):
    """
    Read only meta data for a log message.

    Values must be JSON serializable.

    Automatically serializes as JSON when stringified.
    """
    def __init__(self, **kwargs):
        self._data = kwargs

        # Cache meta data JSON. This will ensure that the meta data
        # is JSON serializable. This is cached on meta change so that
        # it doesn't have to be done every log message.
        self._json = json.dumps(
            # Exclude empty values
            {k: v for k, v in self._data.items() if v not in (None, '')},
            sort_keys=True, separators=(u', ', u':'), ensure_ascii=False)

    def __str__(self):
        """
        Return serialized JSON
        """
        return self._json

    def __bytes__(self):
        """
        Return serialized JSON encoded for UTF-8
        """
        return self._json.encode('utf8')

    def __repr__(self):
        return u'<%s %s>' % (self.__class__.__name__, self._json)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def to_dict(self):
        """
        Returns:
            dict: Dictionary of meta data
        """
        return deepcopy(self._data)


class LogMetaManager(object):
    """
    Track additional metadata for logging. The metadata is stored on
    this instance so this instance can not be re-used for multiple
    requests.

    To add other information to the log output, use ``set_meta``::

        >>> meta = LogMetaManager()
        >>> meta.set_meta(user='foo', nothing=None)
        <LogMeta {"user":"foo"}>
        >>> log = MetaAwareLogger(getter=lambda: meta.get_meta())
        >>> log.info('Test message').meta
        <LogMeta {"user":"foo"}>
    """
    def __init__(self, meta=None):
        self._meta = meta

    def set_meta(self, **kwargs):
        """
        Add metadata to the current meta context

        Args:
            **kwargs: Meta data to add to log records. Must be
                JSON serializable.

        Returns:
            dict: Current meta
        """
        if self._meta:
            d = self._meta.to_dict()
            d.update(kwargs)
            kwargs = d

        self._meta = LogMeta(**kwargs)

        return self._meta

    def get_meta(self):
        """
        Returns:
            LogMeta: Current meta data
        """
        return self._meta

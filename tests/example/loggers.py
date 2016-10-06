import threading
from contextlib import contextmanager

from logaware.logger import AwareLogger, LogLevel, log_method_factory
from logaware.metalogger import MetaAwareLogger, LogMetaManager, LogMeta


class CustomLogger(AwareLogger):
    """
    Logger with additional levels for auditing and debugging.
    """
    # Log for changes that must be audited
    AUDIT = LogLevel(99, 'AUDIT')
    audit = log_method_factory('audit', AUDIT)

    # Log error messages with traceback
    FAIL = LogLevel(100, 'FAIL')
    fail = log_method_factory('fail', FAIL, traceback=True)


# Shared instance for custom logger
# Import this logger into any module and use it's logging methods
custom_log = CustomLogger()

# Shared instance for standard logger
# Import this logger into any module and use it's logging methods
log = AwareLogger()

# Use a thread local to maintain meta data for each thread. This
# works for basic threaded Python applications. For more robust
# handling for threads and co-routines, see Context Locals
# (http://werkzeug.pocoo.org/docs/0.11/local/). If using
# a framework like Flask, consider using ``flask.g``
# (http://flask.pocoo.org/docs/0.11/api/#flask.g)
_meta_local = threading.local()


@contextmanager
def log_meta_context(**kwargs):
    """
    Set log meta data within a context for current thread. Can be nested.

    Each nested context will inherit the meta from the parent context.
    """
    if not hasattr(_meta_local, 'meta'):
        _meta_local.meta = []

    if len(_meta_local.meta):
        # Seems to be a nested context. Include meta from the parent
        # context
        d = _meta_local.meta[-1].to_dict()
        d.update(kwargs)
        kwargs = d

    _meta_local.meta.append(LogMeta(**kwargs))

    yield _meta_local.meta[-1]
    # Remove the current meta from the stack after the context exits
    _meta_local.meta.pop()

# Import this logger into any module and use it's logging methods.
# It will get it's meta data from a ``log_meta_context``.
meta_log = MetaAwareLogger(getter=lambda: _meta_local.meta[-1] if getattr(_meta_local, 'meta', None) else '{}')

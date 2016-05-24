import inspect


class Tester(object):
    def __init__(self, log):
        self._log = log

    def run(self):
        """
        Logs a message and returns the line number that the log
        message is on.
        """
        self._log.info('Logging from within Tester.run')
        return inspect.currentframe().f_lineno - 1


def module_function(log):
    """
    Logs a message and returns the line number that the log message
    is on.
    """
    log.debug('Logging from within module_function')
    return inspect.currentframe().f_lineno - 1
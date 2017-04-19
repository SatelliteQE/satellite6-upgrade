import logging
import os

HIGHLIGHT_LEVEL_NUM = 25
logging.addLevelName(HIGHLIGHT_LEVEL_NUM, 'HIGHLIGHT')


class MyLogger(logging.Logger):
    """New Logger class to add new logger level"""
    def highlight(self, message, *args, **kws):
        """New custom Logger level name highlight

        Created to highlight the main events in logging
        """
        self.log(HIGHLIGHT_LEVEL_NUM, message, *args, **kws)


class SingleLevelClassFilter(logging.Filter):
    """New Logging level class filter"""
    def __init__(self, level, reject):
        """
        :param int level: The level number to filter out
        :param bool reject: Filters if set to False and doesnt filters if True
        """
        self.level = level
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno != self.level)
        else:
            return (record.levelno == self.level)


def logger():
    """Logger to log messages to Console and to files

    This logger creates two files:
    full_upgrade: Contents all logging level logs
    upgrade_highlights: Contents only Highlight logging level logs

    These highlight level logs have been used as contents of Upgrade status
    email sent via jenkins

    :returns object log: Logger object to log different logging levels
    """
    logging.setLoggerClass(MyLogger)
    log = logging.getLogger('upgrade_logging')
    paramiko_logger = logging.getLogger("paramiko.transport")
    paramiko_logger.disabled = True
    if not log.handlers:
        # Log files
        logfile_path = os.path.abspath('full_upgrade')
        highlight_path = os.path.abspath('upgrade_highlights')
        # Hamdlers
        hdlr = logging.FileHandler(logfile_path)
        hdlr2 = logging.FileHandler(highlight_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        ch = logging.StreamHandler()
        # Filters
        f1 = SingleLevelClassFilter(HIGHLIGHT_LEVEL_NUM, False)
        hdlr2.addFilter(f1)
        # Add Handlers
        log.addHandler(hdlr)
        log.addHandler(hdlr2)
        log.addHandler(ch)
        # Set Level
        log.setLevel(logging.INFO)
    return log

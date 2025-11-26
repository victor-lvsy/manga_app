"""
    Logging Module
    ==============

    This module provides a custom Logger class that wraps Python's logging module.
    It adds an additional logging level (DEV) to help track developer-specific debugging
    messages.

    Usage Example:

        from logger import Logger
        logger = Logger(__name__)
        logger.dev("This is a developer level message.")
"""
import logging



class CustomFormatter(logging.Formatter):
    """
    Custom Formatter for logging messages.
    """
    grey = "\x1b[38;20m"
    bold_grey = "\x1b[38;1m"
    yellow = "\x1b[33;20m"
    bold_yellow = "\x1b[33;1m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34;20m"
    bold_blue = "\x1b[34;1m"
    reset = "\x1b[0m"
    green = "\x1b[32;20m"

    fmt = "{asctime} - {levelname}:{name}[{thread_id}] - {message} ({filename}:{lineno})"
    style = "{"
    FORMATS = {
        logging.DEBUG: green + "{asctime} " + reset + blue + "{name}[{thread_id}] " + reset + bold_blue + "{levelname} " + reset +  "{message}",
        logging.INFO: green + "{asctime} " + reset + blue + "{name}[{thread_id}] " + reset + bold_grey + "{levelname} " + reset +  "{message}",
        logging.WARNING: green + "{asctime} " + reset + blue + "{name}[{thread_id}] " + reset + bold_yellow + "{levelname} " + reset +  "{message}",
        logging.ERROR: green + "{asctime} " + reset + blue + "{name}[{thread_id}] " + reset + bold_red + "{levelname} " + reset +  "{message}",
        logging.CRITICAL: green + "{asctime} " + reset + blue + "{name}[{thread_id}] " + reset + bold_red + "{levelname} " + reset +  "{message}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, style=self.style)
        return formatter.format(record)


class Logger:
    """
    Custom Logger Wrapper
    ---------------------

    The Logger class wraps the standard Python logging functionality. It sets up a stream handler that outputs log messages
    to the standard output.

    :param name: The name of the logger.
    :type name: str
    :param level: The logging level threshold. Defaults to logging.INFO.
    :type level: int
    """
    def __init__(self, name, level=logging.DEBUG):

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        fmt = CustomFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def debug(self, msg, thread_id=None):
        """
        Log a message at the DEBUG level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.debug(msg, extra={"thread_id": thread_id})

    def info(self, msg, thread_id=None):
        """
        Log a message at the INFO level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.info(msg, extra={"thread_id": thread_id})

    def warning(self, msg, thread_id=None):
        """
        Log a message at the WARNING level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.warning(msg, extra={"thread_id": thread_id})

    def error(self, msg, thread_id=None):
        """
        Log a message at the ERROR level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.error(msg, extra={"thread_id": thread_id})

    def critical(self, msg, thread_id=None):
        """
        Log a message at the CRITICAL level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.critical(msg, extra={"thread_id": thread_id})


if __name__ == "__main__":
    logger = Logger(__name__)
    logger.debug("This is a debug level message.")
    logger.info("This is an info level message.", thread_id="1234567890")
    logger.warning("This is a warning level message.", thread_id="1234567890")
    logger.error("This is an error level message.", thread_id="1234567890")
    logger.critical("This is a critical level message.", thread_id="1234567890")
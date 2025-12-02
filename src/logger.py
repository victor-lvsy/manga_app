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
import sys
import logging
import asyncio


if sys.argv[1] == "dev":
    log_level = logging.DEBUG
else:
    log_level = logging.INFO


class TaskNameFilter(logging.Filter):
    """
    Filter to add the name of the current task to the logging record.
    """
    def filter(self, record):
        try:
            task = asyncio.current_task()
            if task:
                record.task_name = task.get_name()[:9]
            else:
                record.task_name = "Main"
        except RuntimeError:
            # No running event loop → synchronous context
            record.task_name = "Main"
        return True


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
    bold_white = "\x1b[37;1m"

    fmt = "{asctime} - {levelname}:{name}[{task_name}] - {message} ({filename}:{lineno})"
    style = "{"
    FORMATS = {
        logging.DEBUG: green + "{asctime} " + reset + blue + "{name}[{task_name}] " + reset + bold_blue + "{levelname} " + reset + "{message}",
        logging.INFO: green + "{asctime} " + reset + blue + "{name}[{task_name}] " + reset + bold_white + "{levelname} " + reset + "{message}",
        logging.WARNING: green + "{asctime} " + reset + blue + "{name}[{task_name}] " + reset + bold_yellow + "{levelname} " + reset + "{message}",
        logging.ERROR: green + "{asctime} " + reset + blue + "{name}[{task_name}] " + reset + bold_red + "{levelname} " + reset + "{message}",
        logging.CRITICAL: green + "{asctime} " + reset + blue + "{name}[{task_name}] " + reset + bold_red + "{levelname} " + reset + "{message}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, style=self.style, datefmt="%d/%m/%y %H:%M:%S")
        return formatter.format(record)


class CustomLogLevels:
    """
    Custom Log Levels
    """

    DEBUG = ["worker_context"]
    INFO = ["config", "db-access-layer", "vrf-generator"]


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
    def __init__(self, name, level=log_level):
        self.logger = logging.getLogger(name)
        if name in CustomLogLevels.DEBUG:
            level = logging.DEBUG
        elif name in CustomLogLevels.INFO:
            print(f"Setting level to INFO for {name}")
            level = logging.INFO
        self.logger.setLevel(level)
        fmt = CustomFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)
        self.logger.propagate = False
        self.logger.addFilter(TaskNameFilter())
        self.debug(f"Logger initialized for {name}")

    def debug(self, msg, task_name=None):
        """
        Log a message at the DEBUG level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.debug(msg, extra={"task_name": task_name})

    def info(self, msg, task_name=None):
        """
        Log a message at the INFO level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.info(msg, extra={"task_name": task_name})

    def warning(self, msg, task_name=None):
        """
        Log a message at the WARNING level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.warning(msg, extra={"task_name": task_name})

    def error(self, msg, task_name=None):
        """
        Log a message at the ERROR level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.error(msg, extra={"task_name": task_name})

    def critical(self, msg, task_name=None):
        """
        Log a message at the CRITICAL level.

        :param msg: The message to log.
        :type msg: str
        """
        self.logger.critical(msg, extra={"task_name": task_name})


if __name__ == "__main__":
    logger = Logger(__name__)
    logger.debug("This is a debug level message.")
    logger.info("This is an info level message.", task_name="1234567890")
    logger.warning("This is a warning level message.", task_name="1234567890")
    logger.error("This is an error level message.", task_name="1234567890")
    logger.critical("This is a critical level message.", task_name="1234567890")

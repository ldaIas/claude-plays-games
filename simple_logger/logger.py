"""
Simple logger that helps display log level, line, and any exceptions or objects to pass through.
Primary output target is an sh terminal
"""

import logging
import sys
import inspect
import re

class SimpleLogger:

    def __init__(self, logger_name="", log_level=logging.DEBUG, log_file=None):
        self.logger_instance = self._setup_logger('debug_logger'+logger_name, log_level=log_level, log_file=log_file)


    def _setup_logger(self, logger_name, log_level=logging.DEBUG, log_file=None):
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Make it easy to see new log sessions
        logger.debug("\n--------------------------------------------------" * 2)

        return logger
    

    def _log_with_location(self, level, message, *args, **kwargs):
        caller = inspect.getframeinfo(inspect.currentframe().f_back.f_back)
        
        if isinstance(message, str):
            # Look for PNG header and capture everything until the next quote
            base64_pattern = r'iVBORw0KGgo[^\']*'
            message = re.sub(base64_pattern, '[PNG DATA TRUNCATED]', message)

        formatted_message = f"{caller.filename}:{caller.lineno} - {message}"
        getattr(self.logger_instance, level)(formatted_message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self._log_with_location('debug', message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._log_with_location('info', message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._log_with_location('warning', message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._log_with_location('error', message, *args, **kwargs)



import logging
import os

class Logger:
    def __init__(self, name: str = "polymarket"):
        log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
        log_level = getattr(logging, log_level_str, logging.DEBUG)

        self._logger = logging.getLogger(name)
        self._logger.setLevel(log_level)

        if not self._logger.handlers:
            formatter = logging.Formatter(
                fmt="%(levelname)s <%(asctime)s> %(message)s",
                datefmt="%d/%m/%y> <%H:%M:%S"  # sneaky trick: close/reopen angle brackets
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
            self._logger.addHandler(handler)

    def __getattr__(self, attr):
        # Delegate all attribute access to the internal logger
        return getattr(self._logger, attr)


logger = Logger()

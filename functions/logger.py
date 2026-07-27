"""Shared logging configuration for the review bot."""

import logging

# The format used for each log line so events are easier to diagnose.
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVEL = logging.INFO


def setup_logging(level: int = DEFAULT_LEVEL) -> None:
    """Configure the root logger with the project-wide format and level."""
    logging.basicConfig(format=LOG_FORMAT, level=level)


# Create the main logger instance used across the bot modules.
logger = logging.getLogger("review_bot")

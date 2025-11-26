"""Logging configuration for the recipe parser."""

import logging
import sys


def setup_logging(level: str = "INFO", verbose: bool = False) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        verbose: If True, sets DEBUG level and shows more details
    """
    if verbose:
        level = "DEBUG"

    # Convert string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific levels for verbose output
    if verbose:
        # Show DEBUG for our extractors
        logging.getLogger("epub_recipe_parser.extractors").setLevel(logging.DEBUG)
        logging.getLogger("epub_recipe_parser.core").setLevel(logging.DEBUG)
    else:
        # Show only INFO and above for normal operation
        logging.getLogger("epub_recipe_parser").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

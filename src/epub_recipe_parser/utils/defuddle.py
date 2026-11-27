"""Defuddle HTML cleaning integration.

Defuddle is a library that removes clutter from web pages, leaving only
the main content. This module provides a Python wrapper to call defuddle
via Node.js for HTML pre-processing.
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DefuddleHTMLCleaner:
    """Wrapper for defuddle CLI to clean messy HTML content."""

    _available: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if defuddle CLI is installed and available."""
        if cls._available is not None:
            return cls._available

        try:
            result = subprocess.run(
                ["defuddle", "--version"],
                capture_output=True,
                timeout=5,
            )
            cls._available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            cls._available = False

        return cls._available

    @staticmethod
    def clean_html(html: str, strict: bool = False) -> Optional[str]:
        """Clean messy HTML using defuddle.

        Removes clutter like sidebars, footers, ads, navigation elements,
        leaving only the main content.

        Args:
            html: Input HTML string
            strict: If True, return None on error instead of fallback

        Returns:
            Cleaned HTML string, or None if defuddle unavailable or fails

        Example:
            >>> dirty = '<nav>...</nav><article>Recipe here</article><footer>...</footer>'
            >>> clean = DefuddleHTMLCleaner.clean_html(dirty)
            >>> # Returns only the article content
        """
        if not DefuddleHTMLCleaner.is_available():
            logger.debug("Defuddle not available, skipping HTML cleaning")
            return None

        try:
            result = subprocess.run(
                ["defuddle", "parse"],
                input=html,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            logger.warning(
                f"Defuddle cleaning failed with code {result.returncode}: "
                f"{result.stderr[:200]}"
            )
            return None

        except subprocess.TimeoutExpired:
            logger.warning("Defuddle cleaning timed out")
            return None
        except Exception as e:
            logger.warning(f"Error calling defuddle: {e}")
            return None


def clean_section_html(html: str, use_defuddle: bool = False) -> str:
    """Clean section HTML, optionally using defuddle.

    This is a convenience function that conditionally uses defuddle
    for HTML cleaning if enabled.

    Args:
        html: Input HTML string
        use_defuddle: If True, attempt to clean with defuddle

    Returns:
        Cleaned HTML string (original if defuddle unavailable)
    """
    if not use_defuddle:
        return html

    cleaned = DefuddleHTMLCleaner.clean_html(html)
    if cleaned:
        logger.debug("Successfully cleaned HTML with defuddle")
        return cleaned

    logger.debug("Defuddle cleaning failed or unavailable, using original HTML")
    return html

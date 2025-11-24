"""Text processing utilities."""

import re


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove special markdown/formatting characters
    text = re.sub(r"\{[^}]+\}", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)

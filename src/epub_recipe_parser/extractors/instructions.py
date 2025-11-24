"""Extract cooking instructions from HTML."""

from typing import Optional
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.patterns import (
    INSTRUCTION_KEYWORDS,
    COOKING_VERBS_PATTERN,
)


class InstructionsExtractor:
    """Extract cooking instructions from HTML."""

    @staticmethod
    def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract instructions using multiple strategies."""
        # Strategy 1: Find by header
        instructions = HTMLParser.find_section_by_header(soup, INSTRUCTION_KEYWORDS)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 2: Find numbered lists with cooking verbs
        for list_elem in soup.find_all(["ol", "ul"]):
            items = HTMLParser.extract_from_list(list_elem)
            if not items or len(items) < 2:
                continue

            # Check for cooking verbs
            combined_text = " ".join(items).lower()
            cooking_verbs = COOKING_VERBS_PATTERN.findall(combined_text)

            if len(cooking_verbs) >= 3 and len(combined_text) > 100:
                return "\n\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

        # Strategy 3: Find consecutive paragraphs with cooking verbs
        instruction_paragraphs = []
        in_instruction_section = False

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)
            if len(text_content) < 30:
                continue

            cooking_verbs = len(COOKING_VERBS_PATTERN.findall(text_content.lower()))

            if cooking_verbs >= 2:
                in_instruction_section = True
                instruction_paragraphs.append(text_content)
            elif in_instruction_section and cooking_verbs >= 1:
                instruction_paragraphs.append(text_content)
            elif in_instruction_section and len(instruction_paragraphs) >= 2:
                break

        if len(instruction_paragraphs) >= 2:
            return "\n\n".join(instruction_paragraphs)

        return None

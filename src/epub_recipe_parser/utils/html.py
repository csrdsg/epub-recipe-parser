"""HTML parsing utilities."""

from typing import List, Optional, Tuple
from bs4 import BeautifulSoup


class HTMLParser:
    """Parse and clean HTML content from EPUB."""

    @staticmethod
    def parse_html(content: bytes) -> BeautifulSoup:
        """Parse HTML content to BeautifulSoup."""
        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        return soup

    @staticmethod
    def extract_text(soup: BeautifulSoup) -> str:
        """Extract clean text from BeautifulSoup."""
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        text = "\n".join(line for line in lines if line)

        return text

    @staticmethod
    def extract_from_list(element) -> List[str]:
        """Extract items from HTML list (ol/ul)."""
        items = []
        for li in element.find_all("li", recursive=False):
            text = li.get_text(separator=" ", strip=True)
            if text:
                items.append(text)
        return items

    @staticmethod
    def find_section_by_header(soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
        """Find content section by header keyword with type safety.

        Args:
            soup: BeautifulSoup object to search
            keywords: List of header keywords to match

        Returns:
            Content section text or None if not found
        """
        for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div"]):
            header_text = header.get_text().lower()

            for keyword in keywords:
                if keyword in header_text:
                    # Found the header, now collect content until next header
                    content_parts = []

                    # Type safety: Check if there's a list right after the header
                    next_sibling = header.find_next_sibling()
                    if (
                        next_sibling is not None
                        and hasattr(next_sibling, "name")
                        and next_sibling.name
                    ):
                        if next_sibling.name in ["ol", "ul"]:
                            items = HTMLParser.extract_from_list(next_sibling)
                            return "\n".join(f"- {item}" for item in items)

                    # Otherwise collect text until next header or end
                    for sibling in header.find_next_siblings():
                        # Type safety: Check if sibling has name attribute
                        if not hasattr(sibling, "name") or sibling.name is None:
                            continue

                        if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            break

                        if sibling.name in ["ol", "ul"]:
                            items = HTMLParser.extract_from_list(sibling)
                            content_parts.extend(items)
                        elif sibling.name == "p":
                            text = sibling.get_text(strip=True)
                            if text:
                                content_parts.append(text)

                    if content_parts:
                        return "\n\n".join(content_parts)

        return None

    @staticmethod
    def split_by_headers(
        soup: BeautifulSoup, section_title: Optional[str] = None
    ) -> List[Tuple[str, BeautifulSoup]]:
        """Split an HTML document into sections by headers.

        Args:
            soup: BeautifulSoup object to split
            section_title: Optional title from section tag attribute or TOC
        """
        from collections import Counter

        sections = []

        # Find all headers (h1-h5), prioritizing lower numbers
        all_headers = soup.find_all(["h1", "h2", "h3", "h4", "h5"])

        if not all_headers:
            # No headers found - try alternative title extraction
            extracted_title = HTMLParser._extract_title_from_content(soup)

            # Use section title attribute if available, otherwise use extracted title
            title = section_title or extracted_title or "Untitled"
            return [(title, soup)]

        # Determine the most common header level for splitting
        header_levels = [int(h.name[1]) for h in all_headers]
        if not header_levels:
            title = section_title or HTMLParser._extract_title_from_content(soup) or "Untitled"
            return [(title, soup)]

        # Find the level that appears most frequently (likely recipe level)
        level_counts = Counter(header_levels)
        # Get the smallest level that has good frequency (prefer h2-h3 for recipes)
        split_level = None
        for level in [2, 3, 4, 1, 5]:
            if level_counts.get(level, 0) >= 3:  # At least 3 headers at this level
                split_level = level
                break

        if not split_level:
            # If no clear level, use h3
            split_level = 3

        # Filter headers to only the split level
        headers = [h for h in all_headers if int(h.name[1]) == split_level]

        if not headers:
            # Fall back to all headers
            headers = all_headers

        # Maximum iterations to prevent infinite loops
        MAX_SIBLING_ITERATIONS = 1000

        for i, header in enumerate(headers):
            title = header.get_text(strip=True)

            # Skip if title is too short or looks like a chapter title
            if len(title) < 3 or title.isdigit():
                continue

            # Create a new soup for this section
            section_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
            body = section_soup.body

            # Type safety: Ensure body element exists
            if body is None:
                continue

            # Add the header
            body.append(header.__copy__())

            # Collect elements until next header of same level
            current = header.find_next_sibling()
            iteration_count = 0

            while current is not None and iteration_count < MAX_SIBLING_ITERATIONS:
                iteration_count += 1

                # Type safety: Check current element name exists
                if hasattr(current, "name") and current.name == header.name:
                    # Check if it's a header of same level
                    if current in headers[i + 1 :]:
                        break

                # Add element to section
                body.append(current.__copy__())

                # Type safety: find_next_sibling can return None
                next_sibling = current.find_next_sibling()
                current = next_sibling

            sections.append((title, section_soup))

        return sections

    @staticmethod
    def _extract_title_from_content(soup: BeautifulSoup) -> Optional[str]:
        """Extract title from content using various heuristics when headers are absent.

        Strategies (in order of priority):
        1. Section tag title attribute
        2. First bold/strong text (common in recipe books)
        3. First paragraph if short (< 80 chars)
        4. First significant text line
        """
        # Strategy 1: Check section title attribute
        section = soup.find("section")
        if section:
            title_attr = section.get("title")
            if title_attr and isinstance(title_attr, str):
                title = title_attr.strip()
                if title and len(title) > 3:
                    return title

        # Strategy 2: Look for bold/strong text at the beginning
        # Recipe titles are often the first bold text
        for tag_name in ["b", "strong"]:
            bold_tags = soup.find_all(tag_name, limit=5)
            for bold in bold_tags:
                text = bold.get_text(strip=True)
                # Check if it's likely a title (reasonable length, not all caps unless short)
                if 10 <= len(text) <= 100:
                    # Skip if it looks like a section heading (all caps text > 20 chars)
                    if text.isupper() and len(text) > 20:
                        continue
                    # Skip common non-title patterns
                    lower_text = text.lower()
                    skip_patterns = [
                        "serves",
                        "makes",
                        "for the",
                        "ingredients",
                        "method",
                        "tablespoon",
                        "teaspoon",
                        "cup",
                        "pound",
                        "ounce",
                        "trimmed",
                        "minced",
                        "chopped",
                        "sliced",
                        "diced",
                        "indoor alternative",
                        "outdoor alternative",
                        "coarse salt",
                        "black pepper",
                        "olive oil",
                        "freshly ground",
                    ]
                    if any(skip in lower_text for skip in skip_patterns):
                        continue
                    # Skip if it looks like an ingredient line (contains numbers)
                    if any(char.isdigit() for char in text[:10]):
                        continue
                    return text

        # Strategy 3: First paragraph if short (might be title)
        paragraphs = soup.find_all("p", limit=10)
        for p in paragraphs:
            text = p.get_text(strip=True)
            if 10 <= len(text) <= 80:
                # Check if next element looks like recipe content
                next_elem = p.find_next_sibling()
                if next_elem and next_elem.name == "p":
                    next_text = next_elem.get_text(strip=True)
                    # If next paragraph is longer, this might be a title
                    if len(next_text) > len(text) * 2:
                        return text

        # Strategy 4: First significant line from text
        text = HTMLParser.extract_text(soup)
        if text:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for line in lines[:5]:  # Check first 5 lines
                # Use line if it's reasonable title length
                if 10 <= len(line) <= 100:
                    lower_line = line.lower()
                    # Skip ingredient-like lines
                    skip_patterns = [
                        "tablespoon",
                        "teaspoon",
                        "cup",
                        "pound",
                        "ounce",
                        "trimmed",
                        "minced",
                        "chopped",
                        "sliced",
                        "diced",
                        "indoor alternative",
                        "outdoor alternative",
                        "bay leaves",
                        "bell pepper",
                        "coarse salt",
                        "black pepper",
                        "olive oil",
                        "freshly ground",
                    ]
                    if any(skip in lower_line for skip in skip_patterns):
                        continue
                    # Skip lines starting with numbers
                    if line[0].isdigit():
                        continue
                    return line

        return None

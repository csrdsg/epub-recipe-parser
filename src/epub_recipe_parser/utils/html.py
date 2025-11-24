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
    def find_section_by_header(
        soup: BeautifulSoup, keywords: List[str]
    ) -> Optional[str]:
        """Find content section by header keyword."""
        for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div"]):
            header_text = header.get_text().lower()

            for keyword in keywords:
                if keyword in header_text:
                    # Found the header, now collect content until next header
                    content_parts = []

                    # Check if there's a list right after the header
                    next_sibling = header.find_next_sibling()
                    if next_sibling and next_sibling.name in ["ol", "ul"]:
                        items = HTMLParser.extract_from_list(next_sibling)
                        return "\n".join(f"- {item}" for item in items)

                    # Otherwise collect text until next header or end
                    for sibling in header.find_next_siblings():
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
    def split_by_headers(soup: BeautifulSoup) -> List[Tuple[str, BeautifulSoup]]:
        """Split an HTML document into sections by headers."""
        from collections import Counter

        sections = []

        # Find all headers (h1-h5), prioritizing lower numbers
        all_headers = soup.find_all(["h1", "h2", "h3", "h4", "h5"])

        if not all_headers:
            # No headers, treat whole document as one section
            return [("Untitled", soup)]

        # Determine the most common header level for splitting
        header_levels = [int(h.name[1]) for h in all_headers]
        if not header_levels:
            return [("Untitled", soup)]

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

        for i, header in enumerate(headers):
            title = header.get_text(strip=True)

            # Skip if title is too short or looks like a chapter title
            if len(title) < 3 or title.isdigit():
                continue

            # Create a new soup for this section
            section_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
            body = section_soup.body

            # Add the header
            body.append(header.__copy__())

            # Collect elements until next header of same level
            current = header.find_next_sibling()
            while current:
                # Check if it's a header of same level
                if current.name == header.name and current in headers[i + 1 :]:
                    break

                # Add element to section
                if current:
                    body.append(current.__copy__())
                current = current.find_next_sibling() if current else None

            sections.append((title, section_soup))

        return sections

"""EPUB structure analysis."""

from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


@dataclass
class StructureReport:
    """EPUB structure analysis report."""

    epub_name: str
    title: str
    author: str
    total_items: int
    document_items: int
    image_items: int
    toc_entries: int
    has_toc: bool
    header_distribution: Dict[str, int]
    recipe_indicators: Dict[str, int]


class EPUBStructureAnalyzer:
    """Analyze EPUB internal structure."""

    def analyze_structure(self, epub_path: str | Path) -> StructureReport:
        """Analyze EPUB structure and organization."""
        epub_path = Path(epub_path)

        try:
            book = epub.read_epub(str(epub_path))
        except Exception as e:
            raise ValueError(f"Error reading EPUB: {e}")

        # Get metadata
        title_meta = book.get_metadata("DC", "title")
        title = title_meta[0][0] if title_meta else epub_path.stem

        creator_meta = book.get_metadata("DC", "creator")
        author = creator_meta[0][0] if creator_meta else "Unknown"

        # Get all items
        items = list(book.get_items())
        doc_items = [item for item in items if item.get_type() == ebooklib.ITEM_DOCUMENT]
        image_items = [item for item in items if item.get_type() == ebooklib.ITEM_IMAGE]

        # Analyze TOC
        toc = book.toc
        has_toc = bool(toc)
        toc_count = self._count_toc_entries(toc) if toc else 0

        # Analyze header distribution
        header_dist = self._analyze_headers(doc_items)

        # Check for recipe-specific patterns
        recipe_indicators = self._detect_recipe_patterns(doc_items)

        return StructureReport(
            epub_name=epub_path.name,
            title=title,
            author=author,
            total_items=len(items),
            document_items=len(doc_items),
            image_items=len(image_items),
            toc_entries=toc_count,
            has_toc=has_toc,
            header_distribution=header_dist,
            recipe_indicators=recipe_indicators,
        )

    @staticmethod
    def _count_toc_entries(toc) -> int:
        """Count total TOC entries recursively."""
        count = 0
        for item in toc:
            if isinstance(item, tuple):
                _, children = item
                count += 1 + EPUBStructureAnalyzer._count_toc_entries(children)
            else:
                count += 1
        return count

    @staticmethod
    def _analyze_headers(doc_items) -> Dict[str, int]:
        """Analyze header distribution across documents."""
        header_counts = {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}

        for item in doc_items:
            try:
                content = item.get_content()
                soup = BeautifulSoup(content, "html.parser")

                for level in range(1, 7):
                    headers = soup.find_all(f"h{level}")
                    header_counts[f"h{level}"] += len(headers)
            except:
                continue

        return header_counts

    @staticmethod
    def _detect_recipe_patterns(doc_items) -> Dict[str, int]:
        """Detect recipe-specific patterns in documents."""
        indicators = {
            "ingredients": 0,
            "instructions": 0,
            "directions": 0,
            "serves": 0,
            "yield": 0,
            "prep time": 0,
            "cook time": 0,
        }

        for item in doc_items:
            try:
                content = item.get_content()
                text = content.decode("utf-8", errors="ignore").lower()

                for indicator in indicators:
                    if indicator in text:
                        indicators[indicator] += 1
            except:
                continue

        return indicators

    def print_report(self, report: StructureReport):
        """Print formatted structure report."""
        print(f"\n{'='*70}")
        print(f"📖 {report.epub_name}")
        print(f"{'='*70}\n")

        print("📝 METADATA:")
        print(f"  Title: {report.title}")
        print(f"  Author: {report.author}")

        print(f"\n📚 STRUCTURE:")
        print(f"  Total items: {report.total_items}")
        print(f"  Document items: {report.document_items}")
        print(f"  Image items: {report.image_items}")

        print(f"\n📑 TABLE OF CONTENTS:")
        if report.has_toc:
            print(f"  TOC entries: {report.toc_entries}")
        else:
            print("  No TOC found")

        print(f"\n🔍 HEADER DISTRIBUTION:")
        for level, count in sorted(report.header_distribution.items()):
            if count > 0:
                print(f"  {level}: {count}")

        print(f"\n🍳 RECIPE PATTERNS:")
        for indicator, count in sorted(
            report.recipe_indicators.items(), key=lambda x: -x[1]
        ):
            print(f"  '{indicator}': found in {count}/{report.document_items} documents")

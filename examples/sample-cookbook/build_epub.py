"""Build the small, original EPUB used by the sample cookbook walkthrough."""

import argparse
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from ebooklib import epub


def build_epub(output: Path) -> None:
    book = epub.EpubBook()
    book.set_identifier("epub-recipe-parser-sample")
    book.set_title("Small Kitchen Cookbook")
    book.set_language("en")
    book.add_author("EPUB Recipe Parser Contributors")

    sides = epub.EpubHtml(title="Vegetable Sides", file_name="sides.xhtml", uid="sides")
    sides.content = """
    <section>
      <h1>Vegetable Sides</h1>
      <h2 class="RH" id="carrots">Roasted Carrots with Lemon</h2>
      <p>Serves 2</p>
      <p>Prep time: 10 minutes</p>
      <ul>
        <li>4 carrots, sliced lengthwise</li>
        <li>1 tablespoon olive oil</li>
        <li>1 teaspoon lemon juice</li>
        <li>Salt to taste</li>
      </ul>
      <ol>
        <li>Toss the carrots with the oil and salt and arrange them on a sheet pan.</li>
        <li>Roast at 425°F for 20–25 minutes, turning once.</li>
        <li>Drizzle with lemon juice before serving.</li>
      </ol>
    </section>
    """

    mains = epub.EpubHtml(title="Weeknight Mains", file_name="mains.xhtml", uid="mains")
    mains.content = """
    <section>
      <h1>Weeknight Mains</h1>
      <p class="rechead" id="tofu">Ginger Tofu</p>
      <p class="serve">Serves 2</p>
      <p class="ing">1 pound firm tofu, cut into cubes</p>
      <p class="ing">2 tablespoons soy sauce</p>
      <p class="ing">1 tablespoon grated ginger</p>
      <p class="ing">1 tablespoon neutral oil</p>
      <p class="noindentt">Combine the tofu, soy sauce, ginger, and oil in a bowl.
      Marinate for 30 minutes.</p>
      <p class="noindentt">Spread the cubes on a sheet pan and bake at 400°F
      for 25 minutes. Let the tofu rest for 5 minutes before serving.</p>
    </section>
    """

    book.add_item(sides)
    book.add_item(mains)
    book.add_item(epub.EpubNav())
    book.toc = (
        (sides, [epub.Link("sides.xhtml#carrots", "Roasted Carrots with Lemon", "carrots")]),
        (mains, [epub.Link("mains.xhtml#tofu", "Ginger Tofu", "tofu")]),
    )
    book.spine = [sides, mains]

    # Keep the sample's source identifiers stable across rebuilds.
    packed = BytesIO()
    timestamp = (2026, 1, 1, 0, 0, 0)
    epub.write_epub(packed, book, {"mtime": datetime(*timestamp)})
    with ZipFile(packed) as source, ZipFile(output, "w") as target:
        for entry in source.infolist():
            fixed = ZipInfo(entry.filename, date_time=timestamp)
            target.writestr(fixed, source.read(entry), compress_type=entry.compress_type)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path for the generated EPUB")
    build_epub(parser.parse_args().output)

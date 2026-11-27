"""Portable contract tests for the Knap workflow, using generated EPUBs."""

import json
import shutil
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from ebooklib import epub

from epub_recipe_parser.cli.main import cli
from epub_recipe_parser.structured import extract_book_structure
from epub_recipe_parser.structured.extractor import RUNTIME, _read_source


@pytest.fixture
def cookbook(tmp_path):
    book = epub.EpubBook()
    book.set_identifier("portable-test-book")
    book.set_title("Test & Cookbook")
    book.set_language("en")
    book.add_author("Test Author")
    first = epub.EpubHtml(title="First document", file_name="text/first.xhtml")
    first.content = """<html><body><section><h1>Soup</h1>
        <section id="recipe"><h2>What you need</h2>
        <ul><li>salt <em>and</em> pepper<ul><li>optional lemon</li></ul></li></ul>
        <h2>How to make it</h2><ol start="3"><li>Stir once.</li><li>Serve.</li></ol>
        <p>Short recipes stay.</p><table><tr><td id="cell">one cell</td></tr></table>
        <p><a href="second.xhtml#note">See note</a></p>
        <p><a href="#recipe">Same chapter</a></p>
        <p><a href="second.xhtml">Whole chapter</a></p>
        <p><a href="../text/second.xhtml#legacy">Named anchor</a></p>
        <p><a href="second.xhtml#recipe">Repeated ID</a></p>
        <p><a href="second.xhtml#caf%C3%A9">Unicode anchor</a></p>
        <p><a href="#cell">Table cell</a></p>
        <p><a href="https://example.com/second.xhtml#note">External</a></p>
        <p><a href="second.xhtml#missing">Missing anchor</a></p>
        <p><a href="not-exported.xhtml">Missing chapter</a></p>
        </section></section></body></html>"""
    second = epub.EpubHtml(title="Second document", file_name="text/second.xhtml")
    second.content = """<html><body><p id="note">Unlabelled text: árvíztűrő.</p>
        <a name="legacy"></a><p id="recipe">Repeated source ID.</p>
        <p id="café">Unicode source ID.</p></body></html>"""
    extra = epub.EpubHtml(title="Appendix", file_name="extra.xhtml")
    extra.content = "<html><body><p>Not in reading order</p></body></html>"
    # Manifest order deliberately differs from reading order.
    for item in [first, extra, second]:
        book.add_item(item)
    book.toc = [
        (
            epub.Section("Chapter", "text/first.xhtml"),
            [
                epub.Link("text/first.xhtml#recipe", "Soup", "soup"),
            ],
        )
    ]
    book.add_item(epub.EpubNav())
    book.spine = [second, first]
    path = tmp_path / "cookbook.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def renderer():
    if not shutil.which("node") or not (RUNTIME / "node_modules" / "knap").exists():
        pytest.skip("Run npm ci --prefix src/epub_recipe_parser/structured/runtime first")


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


def test_spine_and_nested_toc(cookbook):
    data = _read_source(cookbook)
    assert [doc["href"] for doc in data["documents"]] == [
        "text/second.xhtml",
        "text/first.xhtml",
    ]
    assert data["toc"][0]["children"][0]["href"] == "text/first.xhtml#recipe"
    assert data["book"]["authors"] == ["Test Author"]
    assert {"code": "document_outside_spine", "href": "extra.xhtml"} in data["warnings"]


def test_structure_and_markdown_preserve_content_once(cookbook, renderer):
    book = extract_book_structure(cookbook)
    assert book.data["mode"] == "source-structure"
    assert len(book.data["documents"]) == 2
    nodes = list(walk(book.data["documents"][1]["structure"]))
    assert sum(node.get("tag") == "section" for node in nodes) == 2
    assert sum(node.get("tag") == "ul" for node in nodes) == 2
    assert any(node.get("attributes", {}).get("start") == "3" for node in nodes)
    assert sum(node.get("content") == "Short recipes stay." for node in nodes) == 1
    assert book.markdown.count("Short recipes stay.") == 1
    assert "salt _and_ pepper" in book.markdown
    assert "3.  Stir once." in book.markdown
    assert "<table>" in book.markdown
    assert "árvíztűrő" in book.markdown
    assert book.markdown.index("Unlabelled text") < book.markdown.index("# Soup")
    assert any(warning["code"] == "no_headings" for warning in book.data["warnings"])
    assert any(warning["code"] == "unresolved_internal_link" for warning in book.data["warnings"])


def test_internal_links_resolve_to_real_unique_markdown_anchors(cookbook, renderer):
    book = extract_book_structure(cookbook)
    second, first = book.data["documents"]
    targets = {
        "See note": second["anchors"]["note"],
        "Same chapter": first["anchors"]["recipe"],
        "Whole chapter": f"#{second['id']}",
        "Named anchor": second["anchors"]["legacy"],
        "Repeated ID": second["anchors"]["recipe"],
        "Unicode anchor": second["anchors"]["café"],
        "Table cell": first["anchors"]["cell"],
    }
    for label, target in targets.items():
        assert f"[{label}]({target})" in book.markdown
        assert book.markdown.count(f'<a id="{target[1:]}"></a>') == 1
    assert first["anchors"]["recipe"] != second["anchors"]["recipe"]
    assert book.data["toc"][0]["export_href"] == f"#{first['id']}"
    assert book.data["toc"][0]["children"][0]["export_href"] == first["anchors"]["recipe"]
    assert "\u200b" not in book.markdown
    assert "data-export-anchor" not in book.markdown


def test_unresolved_and_external_links_keep_source_targets(cookbook, renderer):
    book = extract_book_structure(cookbook)
    assert "[External](https://example.com/second.xhtml#note)" in book.markdown
    assert "[Missing anchor](second.xhtml#missing)" in book.markdown
    assert "[Missing chapter](not-exported.xhtml)" in book.markdown
    warnings = [w for w in book.data["warnings"] if w["code"] == "unresolved_internal_link"]
    assert {w["href"] for w in warnings} == {"second.xhtml#missing", "not-exported.xhtml"}
    first = book.data["documents"][1]
    assert 'href="second.xhtml#note"' in first["source_html"]
    assert any(
        node.get("attributes", {}).get("href") == "second.xhtml#note"
        for node in walk(first["structure"])
    )


def test_custom_knap_template(cookbook, renderer, tmp_path):
    template = tmp_path / "custom.knap.md"
    template.write_text(
        "{{ book.title | upper }}\n{% for doc in documents %}{{ doc.href }}\n{% endfor %}",
        encoding="utf-8",
    )
    result = extract_book_structure(cookbook, template)
    assert result.markdown == "TEST & COOKBOOK\ntext/second.xhtml\ntext/first.xhtml"


def test_cli_writes_reusable_json_and_markdown(cookbook, renderer, tmp_path):
    destination = tmp_path / "export"
    result = CliRunner().invoke(cli, ["structure", str(cookbook), "-o", str(destination)])
    assert result.exit_code == 0, result.output
    data = json.loads((destination / "book.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["documents"][0]["structure"]
    assert (destination / "book.md").read_text(encoding="utf-8").count("Stir once.") == 1


def test_cli_refuses_existing_output(cookbook, tmp_path):
    destination = tmp_path / "export"
    destination.mkdir()
    marker = destination / "book.md"
    marker.write_text("Keep my edits", encoding="utf-8")
    with patch("epub_recipe_parser.cli.structure.extract_book_structure") as extract:
        result = CliRunner().invoke(cli, ["structure", str(cookbook), "-o", str(destination)])
    assert result.exit_code == 1
    extract.assert_not_called()
    assert marker.read_text(encoding="utf-8") == "Keep my edits"


def test_invalid_template_creates_no_export(cookbook, renderer, tmp_path):
    template = tmp_path / "bad.knap.md"
    template.write_text("{{ book.title | missing_filter }}", encoding="utf-8")
    destination = tmp_path / "export"
    result = CliRunner().invoke(
        cli,
        [
            "structure",
            str(cookbook),
            "-o",
            str(destination),
            "--template",
            str(template),
        ],
    )
    assert result.exit_code == 1
    assert "missing_filter" in result.output
    assert not destination.exists()


def test_missing_runtime_has_actionable_error(cookbook):
    with patch("epub_recipe_parser.structured.extractor.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="Node.js 20"):
            extract_book_structure(cookbook)


def test_missing_spine_document_fails_explicitly(cookbook):
    book = epub.read_epub(str(cookbook))
    book.spine = [("missing-id", "yes")]
    with patch("epub_recipe_parser.structured.extractor.epub.read_epub", return_value=book):
        with pytest.raises(ValueError, match="missing-id"):
            _read_source(cookbook)


def test_self_closing_xhtml_keeps_sibling_nesting(cookbook, renderer, tmp_path):
    source = epub.read_epub(str(cookbook))
    item = source.get_item_with_href("text/first.xhtml")
    item.content = b"""<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <section><span id="empty"/><p>First paragraph.</p>
        <a id="destination"/><h2>Second heading.</h2>
        <p>Last paragraph.<br/>After break.</p></section></body></html>"""
    path = tmp_path / "self-closing.epub"
    epub.write_epub(str(path), source)
    book = extract_book_structure(path)
    document = book.data["documents"][1]
    section = next(node for node in document["structure"] if node.get("tag") == "section")
    children = [node for node in section["children"] if node["type"] == "element"]
    assert [node["tag"] for node in children] == ["span", "p", "a", "h2", "p"]
    assert not children[0].get("children")
    assert not children[2].get("children")
    assert "Second heading." in document["markdown"]
    assert document["anchors"]["destination"][1:] in document["markdown"]
    assert "Last paragraph." in document["markdown"]

"""Find recipe boundaries from semantic markup and sibling structure."""

from collections import Counter
from copy import copy
import re

from bs4 import BeautifulSoup, Tag

from epub_recipe_parser.core.patterns.ingredient_detectors import IngredientPatternDetector
from epub_recipe_parser.utils.patterns import COOKING_VERBS_PATTERN, MEASUREMENT_PATTERN

_HEADINGS = {f"h{level}": level for level in range(1, 7)}
_RECIPE_TYPE = '[itemtype~="https://schema.org/Recipe"], [itemtype~="http://schema.org/Recipe"]'
_QUANTITY = re.compile(
    r"^(?:(?:about|approximately|scant|heaping)\s+)?(?P<amount>\d|[¼½¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])",
    re.IGNORECASE,
)
_STEP_NUMBER = re.compile(r"^\d+[.)]\s+")
_RANGE_START = re.compile(r"\d+(?:\.\d+)?\s*(?:[-–—]|to)\s*", re.IGNORECASE)
_COMPONENT_LABEL = re.compile(
    r"^(?:serves?|servings?|yields?|makes?|ingredients?|directions?|instructions?|method"
    r"|prep(?:aration)? time|cook(?:ing)? time|for the|to serve|to finish|menu for"
    r"|chapter\s+\d+|part\s+\d+)(?:\b|:)",
    re.IGNORECASE,
)
_YIELD_LABEL = re.compile(r"^(?:serves?|servings?|yields?|makes?)\b", re.IGNORECASE)
_FOOD = IngredientPatternDetector.INGREDIENT_NOUN_PATTERN


def _text(tag: Tag) -> str:
    return tag.get_text(" ", strip=True)


def _profile(tag: Tag) -> tuple[str, ...]:
    """Group sibling elements by style without assigning meaning to its name."""
    return tuple(sorted(tag.get("class", [])))


def _quantified_ingredient(tag: Tag) -> bool:
    text = _text(tag)
    quantity = _QUANTITY.match(text)
    if not quantity:
        return False
    amount_start = quantity.start("amount")
    range_start = _RANGE_START.match(text, amount_start)
    measure_start = range_start.end() if range_start else amount_start
    words = text.split()
    return bool(
        not _STEP_NUMBER.match(text)
        and len(words) <= 28
        and (
            MEASUREMENT_PATTERN.match(text, measure_start)
            or _FOOD.search(" ".join(text.split(":", 1)[0].split()[:6]))
        )
    )


def _section(title: Tag | str, siblings: list[Tag], ingredients: list[Tag], steps: list[Tag]):
    soup = BeautifulSoup("", "html.parser")
    if isinstance(title, Tag):
        soup.append(copy(title))
    ingredients_ids = {id(element) for element in ingredients}
    step_ids = {id(element) for element in steps}
    for element in siblings:
        cloned = copy(element)
        if id(element) in ingredients_ids:
            cloned["data-recipe-component"] = "ingredients"
        elif id(element) in step_ids:
            cloned["data-recipe-component"] = "instructions"
        soup.append(cloned)
    return _text(title) if isinstance(title, Tag) else title, soup


def _semantic_sections(wrappers: list[Tag]) -> list[tuple[str, BeautifulSoup]]:
    sections = []
    for wrapper in wrappers:
        section = BeautifulSoup("", "html.parser")
        section.append(copy(wrapper))
        title = section.select_one('[itemprop~="name"]')
        name = str(title.get("content") or _text(title)) if title else ""
        ingredients = section.select('[itemprop~="recipeIngredient"]')
        steps = section.select('[itemprop~="recipeInstructions"] [itemprop~="text"]')
        if not steps:
            steps = section.select('[itemprop~="recipeInstructions"]')
        if name and ingredients and steps:
            for item in ingredients:
                item["data-recipe-component"] = "ingredients"
            for step in steps:
                step["data-recipe-component"] = "instructions"
            sections.append((name, section))
    return sections


def _paragraph_headings(soup: BeautifulSoup) -> list[Tag]:
    """Find short titles through anchors, yields, or recurring sibling patterns."""
    candidates = []
    repeated = Counter()
    ingredient_styles = set()
    headed_parents = {id(heading.parent) for heading in soup.find_all(["h2", "h3", "h4", "h5", "h6"])}
    for paragraph in soup.find_all("p"):
        pattern = (id(paragraph.parent), _profile(paragraph))
        if _quantified_ingredient(paragraph):
            ingredient_styles.add(pattern)
            continue
        following = paragraph.find_next_sibling()
        title = _text(paragraph)
        if not title or len(title.split()) > 14 or len(title) > 115 or title.endswith((".", ":")):
            continue
        if _QUANTITY.match(title) or _COMPONENT_LABEL.match(title):
            continue
        has_yield = following is not None and bool(_YIELD_LABEL.match(_text(following)))
        adjacent = following is not None and following.name == "p" and _quantified_ingredient(following)
        if adjacent:
            repeated[pattern] += 1
        if has_yield or adjacent:
            candidates.append((paragraph, has_yield, adjacent, pattern))
    return [
        paragraph for paragraph, has_yield, adjacent, pattern in candidates
        if pattern not in ingredient_styles and (
            has_yield or (adjacent and (
                paragraph.has_attr("id")
                or (pattern[0] not in headed_parents and repeated[pattern] >= 2)
            ))
        )
    ]


def _find_components(siblings: list[Tag]) -> tuple[list[Tag], list[Tag]]:
    lists = []
    for element in siblings:
        if element.name == "ul" and any(
            _quantified_ingredient(item) or (
                len(_text(item).split()) <= 12 and _FOOD.search(_text(item))
            )
            for item in element.find_all("li", recursive=False)
        ):
            lists.append(element)
        elif element.name == "ol" and lists and COOKING_VERBS_PATTERN.search(_text(element)):
            return lists, [element]

    # A lower-level heading can introduce another complete recipe or a variant.
    # Keep each paragraph run within its own heading.
    paragraphs = []
    has_quantified = False
    for element in siblings:
        if element.name in _HEADINGS and has_quantified:
            break
        if element.name == "p" and _text(element):
            paragraphs.append(element)
            has_quantified = has_quantified or _quantified_ingredient(element)
    measured = [element for element in paragraphs if _quantified_ingredient(element)]
    if not measured:
        return [], []
    profiles = Counter(_profile(element) for element in measured)
    profile = profiles.most_common(1)[0][0]

    def is_ingredient(element: Tag) -> bool:
        text = _text(element)
        return _quantified_ingredient(element) or bool(
            profile and _profile(element) == profile and len(text.split()) <= 28
            and not _STEP_NUMBER.match(text)
        )

    start = next(i for i, element in enumerate(paragraphs) if _quantified_ingredient(element))
    while start and is_ingredient(paragraphs[start - 1]):
        start -= 1
    ingredients = []
    end = start
    for position, element in enumerate(paragraphs[start:], start):
        if is_ingredient(element):
            ingredients.append(element)
        elif not (
            _text(element).endswith(":")
            and position + 1 < len(paragraphs)
            and is_ingredient(paragraphs[position + 1])
        ):
            break
        end = position + 1
    following = paragraphs[end:]
    steps = [element for element in following if COOKING_VERBS_PATTERN.search(_text(element))]
    if steps:
        first_step = next(i for i, element in enumerate(following) if element is steps[0])
        step_styles = {_profile(element) for element in steps if _profile(element)}
        steps = [
            element for element in following[first_step:]
            if _profile(element) in step_styles or COOKING_VERBS_PATTERN.search(_text(element))
        ]
    return ingredients, steps


def find_structured_sections(soup: BeautifulSoup) -> list[tuple[str, BeautifulSoup]]:
    """Find recipes from explicit data or repeated headings with both components."""
    wrappers = soup.select(_RECIPE_TYPE)
    wrapper_ids = {id(wrapper) for wrapper in wrappers}
    semantic = _semantic_sections(wrappers)

    sections = {}
    paragraph_headings = _paragraph_headings(soup)
    paragraph_ids = {id(heading) for heading in paragraph_headings}
    headings = soup.find_all(lambda tag: tag.name in _HEADINGS or id(tag) in paragraph_ids)
    for heading in headings:
        if heading.find_parent(["aside", "nav"]) or any(
            id(parent) in wrapper_ids for parent in heading.parents
        ):
            continue
        level = _HEADINGS.get(heading.name)
        if _COMPONENT_LABEL.match(_text(heading)):
            continue
        siblings = []
        for sibling in heading.find_next_siblings():
            next_level = _HEADINGS.get(sibling.name)
            if (next_level and (level is None or next_level <= level)) or (
                level is None and id(sibling) in paragraph_ids
            ):
                break
            if sibling.name not in {"aside", "nav"}:
                siblings.append(sibling)
        ingredients, steps = _find_components(siblings)
        if ingredients and steps:
            key = id(ingredients[0])
            # Prefer a recipe-level heading to the chapter heading above it.
            rank = 7 if level == 1 else level or 0
            if key not in sections or rank < sections[key][0]:
                anchored = heading.has_attr("id") or heading.find("a", id=True) is not None
                sections[key] = (rank, anchored, _section(heading, siblings, ingredients, steps))

    # A single inferred pair can be a sidebar inside a larger section.
    # Require a repeated layout unless markers explicitly identify the recipe.
    return semantic + [
        candidate for _, anchored, candidate in sections.values()
        if anchored or len(sections) > 1 or len(headings) == 1
    ]

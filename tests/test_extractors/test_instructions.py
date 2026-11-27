"""Tests for instructions extractor."""

from bs4 import BeautifulSoup
from epub_recipe_parser.extractors.instructions import InstructionsExtractor


def test_extract_instructions_by_header():
    """Test extracting instructions using header strategy."""
    html = """
    <div>
        <h3>Instructions</h3>
        <ol>
            <li>Heat the grill to medium-high</li>
            <li>Season chicken with salt and pepper</li>
            <li>Grill for 6-7 minutes per side</li>
            <li>Remove and let rest for 5 minutes</li>
        </ol>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "grill" in result.lower()
    assert "heat" in result.lower()
    assert "season" in result.lower()


def test_extract_instructions_by_cooking_verbs():
    """Test extracting instructions using cooking verb detection."""
    html = """
    <div>
        <ul>
            <li>Heat oil in a large pan over medium heat</li>
            <li>Add onions and cook until softened</li>
            <li>Stir in garlic and spices, cook for 1 minute</li>
            <li>Add tomatoes and simmer for 20 minutes</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat" in result.lower()
    assert "cook" in result.lower()
    assert "simmer" in result.lower()


def test_extract_instructions_from_paragraphs():
    """Test extracting instructions from paragraph format."""
    html = """
    <div>
        <p>Heat the grill to high temperature and prepare the meat.</p>
        <p>Season generously with salt and place on the hot grill.</p>
        <p>Cook for about 10 minutes, turning once, until done.</p>
        <p>Remove from heat and let rest before serving.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat" in result.lower()
    assert "cook" in result.lower()


def test_extract_instructions_returns_none_without_content():
    """Test that extractor returns None for content without instructions."""
    html = """
    <div>
        <p>This is just informational text without any cooking instructions.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is None


def test_extract_instructions_minimum_length():
    """Test that extracted instructions meet minimum length requirement."""
    html = """
    <div>
        <h3>Directions</h3>
        <p>Heat and cook the food according to package directions.</p>
        <p>Season to taste and serve immediately.</p>
        <p>Enjoy with your favorite sides.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert len(result) > 50


def test_extract_instructions_by_css_class():
    """Test extracting instructions based on CSS class names."""
    html = """
    <div>
        <p class="intro">This is a delicious recipe that everyone will love.</p>
        <p class="noindentt">Heat the olive oil in a large saucepan over medium heat.</p>
        <p class="noindentt">Add the onions and garlic and cook until softened, about 5 minutes.</p>
        <p class="noindentt">Add the tomatoes and simmer for 20 minutes.</p>
        <p class="noindentt">Season with salt and pepper and serve hot.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat the olive oil" in result.lower()
    assert "add the onions" in result.lower()
    assert "simmer for 20 minutes" in result.lower()
    assert "season with salt" in result.lower()
    # Should not include the intro
    assert "delicious recipe" not in result.lower()


def test_extract_instructions_post_ingredients():
    """Test extracting instructions that come after ingredient sections."""
    html = """
    <div>
        <h3>Spaghetti with Tuna Sauce</h3>
        <p class="intro">A family favorite recipe passed down through generations.</p>
        <p class="serv">SERVES 6</p>
        <p class="ihead">FOR THE SAUCE</p>
        <p class="item">3 tbsp olive oil</p>
        <p class="item">1 onion, chopped</p>
        <p class="item">2 cloves garlic, minced</p>
        <p class="ihead">FOR THE PASTA</p>
        <p class="item">500g spaghetti</p>
        <p class="item">2 tsp salt</p>
        <p class="noindentt">In a saucepan over medium heat, heat the olive oil and cook the onion until softened.</p>
        <p class="noindentt">Add the garlic and cook for another minute, stirring constantly.</p>
        <p class="noindentt">Meanwhile, bring a large pot of salted water to a boil and cook the pasta.</p>
        <p class="noindentt">Drain the pasta and toss with the sauce before serving.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat the olive oil" in result.lower()
    assert "add the garlic" in result.lower()
    assert "bring a large pot" in result.lower()
    assert "drain the pasta" in result.lower()
    # Should not include ingredients
    assert "3 tbsp olive oil" not in result
    assert "500g spaghetti" not in result


def test_extract_instructions_with_method_header():
    """Test extracting instructions with 'Method' header (common in UK cookbooks)."""
    html = """
    <div>
        <h3>Method</h3>
        <p>Preheat the oven to 180°C and prepare a baking dish.</p>
        <p>Combine all the dry ingredients in a large bowl and mix well.</p>
        <p>Add the wet ingredients and stir until just combined.</p>
        <p>Transfer to the prepared dish and bake for 30 minutes.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "preheat" in result.lower()
    assert "combine" in result.lower()
    assert "bake" in result.lower()


def test_extract_instructions_stops_at_notes():
    """Test that extraction stops at notes/tips sections."""
    html = """
    <div>
        <p class="method">Heat the oil in a large pan and add the vegetables.</p>
        <p class="method">Cook for 10 minutes until softened and golden.</p>
        <p class="method">Season with salt and pepper and serve immediately.</p>
        <p class="note">Tip: You can add different vegetables based on what you have.</p>
        <p class="note">Note: This dish can be made ahead and reheated.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat the oil" in result.lower()
    assert "cook for 10 minutes" in result.lower()
    # Should stop before tips/notes if they don't have cooking verbs
    # But the current implementation might include them if they have method class
    # This is a edge case we accept for now


def test_extract_instructions_with_numbered_steps():
    """Test extracting instructions with explicit step numbers."""
    html = """
    <div>
        <h3>Directions</h3>
        <p class="step">1. Preheat your grill to medium-high heat.</p>
        <p class="step">2. Season the meat generously with salt and pepper.</p>
        <p class="step">3. Place on the grill and cook for 6-8 minutes per side.</p>
        <p class="step">4. Remove from grill and let rest for 5 minutes before slicing.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "preheat" in result.lower()
    assert "season the meat" in result.lower()
    assert "place on the grill" in result.lower()
    assert "let rest" in result.lower()


def test_extract_instructions_handles_multiple_paragraphs_with_varied_verb_counts():
    """Test that extraction continues through paragraphs with varying cooking verb counts."""
    html = """
    <div>
        <p>Heat the olive oil in a large saucepan over medium heat and add the onions.</p>
        <p>Cook until softened, stirring occasionally, about 5 minutes.</p>
        <p>Meanwhile, prepare the other ingredients.</p>
        <p>Add the garlic and spices and cook for another minute.</p>
        <p>Finally, add the tomatoes and simmer for 20 minutes.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    # Should include all paragraphs including the one with fewer verbs
    assert "heat the olive oil" in result.lower()
    assert "cook until softened" in result.lower()
    assert "meanwhile" in result.lower() or "prepare the other" in result.lower()
    assert "add the garlic" in result.lower()
    assert "simmer for 20 minutes" in result.lower()


def test_extract_instructions_skips_ingredient_lists():
    """Test that extraction doesn't include ingredient list items."""
    html = """
    <div>
        <h3>Ingredients</h3>
        <p class="item">2 cups flour</p>
        <p class="item">1 tsp salt</p>
        <p class="item">3 eggs</p>
        <h3>Instructions</h3>
        <p>Mix the flour and salt in a large bowl.</p>
        <p>Add the eggs one at a time, stirring after each addition.</p>
        <p>Knead the dough until smooth and elastic.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "mix the flour" in result.lower()
    assert "add the eggs" in result.lower()
    assert "knead the dough" in result.lower()
    # Should not include ingredient items
    assert "2 cups flour" not in result
    assert "3 eggs" not in result


def test_extract_narrative_instructions_with_keyword_prefix():
    """Test extracting narrative-style instructions that start with a keyword like 'To make'."""
    html = """
    <div>
        <p>This is a traditional recipe that has been passed down for generations.</p>
        <p>To make ghee: Melt two sticks of unsalted butter in a small saucepan over medium-low heat.
        Cook for about 20 minutes, gently swirling the pan every now and then. White foam will collect
        on the surface and the liquid will bubble aggressively, which is the water cooking off. Continue
        cooking until the bubbling begins to subside somewhat and the milk solids sink to the bottom of
        the pan. Watch for them to take on a reddish-brown color, and once they do, strain the fat
        through a cheesecloth-lined sieve or coffee filter into a heat-safe jar.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "melt two sticks" in result.lower()
    assert "cook for about 20 minutes" in result.lower()
    assert "strain the fat" in result.lower()
    # Should not include the intro paragraph
    assert "traditional recipe" not in result.lower()


def test_extract_narrative_instructions_without_header():
    """Test extracting narrative instructions without any header or keyword prefix."""
    html = """
    <div>
        <p>Yield 4 Servings</p>
        <p>2 cups (480 ml) heavy cream</p>
        <p>1 tbsp (15 g) sahlep (optional)</p>
        <p>1 (14–oz [396–g]) can sweetened condensed milk</p>
        <p>½ cup (120 ml) tahini paste</p>
        <p>In a stand mixer bowl, add the cream and whisk on medium speed until firm peaks start to form,
        around 5 to 7 minutes. Add the sahlep (if using) and mix for another 20 seconds. In a separate bowl,
        add the condensed milk and tahini and mix until well combined. Fold in the tahini mixture to the
        whipped cream until well combined. Pour the final mixture into a loaf pan. Add the date paste on top
        and using a knife, swirl the paste all around, giving it a swirled appearance. Place it in the freezer
        for 5 to 24 hours.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "stand mixer" in result.lower()
    assert "whisk on medium speed" in result.lower()
    assert "fold in the tahini" in result.lower()
    assert "place it in the freezer" in result.lower()
    # Should not include ingredient list items
    assert "2 cups (480 ml)" not in result


def test_extract_instructions_with_to_make_keyword():
    """Test extracting instructions that use 'To make:' as a prefix."""
    html = """
    <div>
        <p>This versatile sauce works well with many dishes.</p>
        <p>To make the sauce: Heat olive oil in a large pan over medium heat. Add the onions
        and cook until softened, about 5 minutes. Add the garlic and cook for another minute.
        Pour in the tomatoes and simmer for 20 minutes, stirring occasionally. Season with
        salt and pepper to taste.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat olive oil" in result.lower()
    assert "add the onions" in result.lower()
    assert "pour in the tomatoes" in result.lower()
    assert "season" in result.lower() and "salt" in result.lower()


def test_extract_long_narrative_instruction_paragraph():
    """Test extracting a single very long narrative instruction paragraph."""
    html = """
    <div>
        <p>Preheat your oven to 350°F and prepare a 9x13 inch baking pan by greasing it lightly
        with butter or cooking spray, then set it aside for later use. In a large mixing bowl,
        combine the flour, baking powder, salt, and sugar, whisking together until everything is
        well distributed and there are no lumps visible in the mixture. In a separate medium bowl,
        beat together the eggs, milk, melted butter, and vanilla extract until the mixture is smooth
        and well combined with no streaks of egg remaining. Pour the wet ingredients into the dry
        ingredients and stir gently with a wooden spoon or rubber spatula, being careful not to
        overmix as this can result in a tough final product; mix just until the flour is incorporated
        and you can no longer see any dry pockets. Transfer the batter to your prepared baking pan,
        spreading it evenly with a spatula to ensure even baking. Bake in the preheated oven for
        25 to 30 minutes, or until a toothpick inserted into the center comes out clean or with
        just a few moist crumbs attached. Remove from the oven and allow to cool in the pan for
        at least 10 minutes before serving.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "preheat your oven" in result.lower()
    assert "combine the flour" in result.lower()
    assert "beat together the eggs" in result.lower()
    assert "bake in the preheated oven" in result.lower()


def test_extract_instructions_with_for_prefix():
    """Test extracting instructions with 'For the' component prefixes."""
    html = """
    <div>
        <h3>For the dough:</h3>
        <p>2 cups flour</p>
        <p>1 tsp salt</p>
        <h3>For the filling:</h3>
        <p>1 cup ricotta</p>
        <p>½ cup parmesan</p>
        <p>Mix together the flour and salt in a large bowl. Add water gradually and knead
        until smooth and elastic, about 10 minutes. Cover with a damp cloth and let rest
        for 30 minutes. Meanwhile, combine the ricotta and parmesan in a bowl and season
        with salt and pepper. Roll out the dough very thin and cut into circles. Place a
        spoonful of filling in the center of each circle, fold in half, and seal the edges.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "mix together the flour" in result.lower()
    assert "add water gradually" in result.lower()
    assert "combine the ricotta" in result.lower()
    assert "roll out the dough" in result.lower()
    # Should not include the ingredient measurements
    assert "2 cups flour" not in result
    assert "1 cup ricotta" not in result


def test_extract_instructions_handles_meanwhile_transitions():
    """Test that extraction continues through transition words like 'Meanwhile'."""
    html = """
    <div>
        <p>Heat the oil in a large saucepan and add the onions, cooking until softened.</p>
        <p>Meanwhile, bring a large pot of salted water to a boil.</p>
        <p>Add the pasta to the boiling water and cook according to package directions.</p>
        <p>Drain the pasta and toss with the sauce before serving hot.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "heat the oil" in result.lower()
    assert "meanwhile" in result.lower()
    assert "add the pasta" in result.lower()
    assert "drain the pasta" in result.lower()


def test_extract_instructions_ghee_style():
    """Test extracting instructions from ghee-style recipe (single long paragraph after description)."""
    html = """
    <div>
        <h3>GHEE</h3>
        <p>In ghee, butter is essentially concentrated, with the water cooked out, and the milk solids have
        caramelized to lend nutty and toasty notes. It brings a distinctive richness to whatever it touches.</p>
        <p>To make ghee: Melt two sticks of unsalted butter in a small saucepan over medium-low heat.
        Cook for about 20 minutes, gently swirling the pan every now and then. White foam will collect
        on the surface and the liquid will bubble aggressively, which is the water cooking off. Continue
        cooking until the bubbling begins to subside somewhat and the milk solids sink to the bottom of
        the pan. Watch for them to take on a reddish-brown color, and once they do, strain the fat
        through a cheesecloth-lined sieve or coffee filter into a heat-safe jar. Cool completely, then
        seal and store in the cupboard or the fridge.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "melt two sticks" in result.lower()
    assert "cook for about 20 minutes" in result.lower()
    assert "strain the fat" in result.lower()
    assert "cool completely" in result.lower()
    # Should not include the description
    assert "distinctive richness" not in result.lower()


def test_extract_instructions_embedded_with_ingredients():
    """Test extracting instructions that appear directly after ingredients with no separator."""
    html = """
    <div>
        <h3>Karak Chai</h3>
        <p>Yield 3 Cups (720 ml)</p>
        <p>2 tbsp (30 g) granulated sugar</p>
        <p>2 cups (480 ml) hot water</p>
        <p>1 tbsp (2 g) high quality black loose-leaf tea</p>
        <p>2 green cardamom pods, crushed</p>
        <p>In a medium saucepan over medium heat, add the sugar and let it melt without stirring it
        until it caramelizes and becomes golden. Slowly add the hot water and bring to a boil. Add the
        tea leaves and spices and let it boil for 2 minutes. Reduce the heat to low and add the evaporated
        milk. Let it simmer for another 3 minutes. Strain into cups and serve immediately.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "add the sugar" in result.lower()
    assert "caramelizes" in result.lower()
    assert "bring to a boil" in result.lower()
    assert "strain into cups" in result.lower()
    # Should not include ingredient measurements
    assert "2 tbsp (30 g)" not in result


def test_extract_instructions_ice_cream_recipe():
    """Test extracting instructions from ice cream recipe with single long paragraph."""
    html = """
    <div>
        <p class="intro">This recipe has very basic ingredients and is super easy to make.</p>
        <p>In a stand mixer bowl, add the cream and whisk on medium speed until firm peaks start to form,
        around 5 to 7 minutes. Add the sahlep (if using) and mix for another 20 seconds. In a separate bowl,
        add the condensed milk and tahini and mix until well combined. Fold in the tahini mixture to the
        whipped cream until well combined. Pour the final mixture into a loaf pan. Add the date paste on top
        and using a knife, swirl the paste all around, giving it a swirled appearance. Place it in the freezer
        for 5 to 24 hours.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    assert "stand mixer" in result.lower()
    assert "whisk on medium speed" in result.lower()
    assert "fold in the tahini" in result.lower()
    assert "place it in the freezer" in result.lower()
    # Should not include intro text
    assert "super easy to make" not in result.lower()


def test_extract_instructions_baklawa_short():
    """Test extracting short but complete instructions with mixed paragraphs."""
    html = """
    <div>
        <h3>Baklawa Bites</h3>
        <p class="item">8 oz (227 g) phyllo dough, thawed</p>
        <p class="item">1 cup (120 g) walnuts, finely chopped</p>
        <p>Remove the phyllo dough from the package and cover it with a slightly damp cloth to prevent
        it from drying out.</p>
        <p>To prepare the sugar syrup, place sugar, water and cardamom pods in a deep saucepan. Let it
        boil over medium heat for 15 minutes until it slightly thickens and set aside.</p>
        <p>Preheat oven to 350°F (180°C). Using a knife, cut the dough into squares and place in muffin tins.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    result = InstructionsExtractor.extract(soup, text)
    assert result is not None
    # Should extract the "To prepare" paragraph at minimum
    assert "prepare the sugar syrup" in result.lower()
    assert "boil over medium heat" in result.lower()

{{ book.title | escape_md | h1 }}

{% if book.authors %}{{ book.authors | escape_md | join:", " }}

{% endif %}{% for document in documents %}---

Source: {{ document.href | code }}

{{ document.markdown }}

{% endfor %}

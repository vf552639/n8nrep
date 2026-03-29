"""Programmatic merge of article HTML into a site template (no LLM)."""

from bs4 import BeautifulSoup


def _append_parsed_fragment(container, content_html: str) -> None:
    container.clear()
    frag = BeautifulSoup(content_html, "html.parser")
    source = frag.body if frag.body else frag
    for node in list(source.children):
        if getattr(node, "name", None) is None and not str(node).strip():
            continue
        container.append(node.extract())


def programmatic_html_insert(template_html: str, content_html: str) -> str:
    """
    Insert article HTML into a template without an LLM.
    Tries {{content}} placeholder, then common containers (main, article, #content, etc.).
    """
    if not template_html or not str(template_html).strip():
        return content_html

    if "{{content}}" in template_html:
        return template_html.replace("{{content}}", content_html)

    soup = BeautifulSoup(template_html, "html.parser")
    container = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", id="content")
        or soup.find("div", class_="content")
        or soup.find("div", class_="post-content")
        or soup.find("div", class_="entry-content")
    )

    if container:
        _append_parsed_fragment(container, content_html)
        return str(soup)

    return content_html

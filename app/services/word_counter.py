import re

from bs4 import BeautifulSoup


def count_content_words(html_or_text: str) -> int:
    """Count visible text words (strip HTML); tags and attributes are ignored."""
    if not html_or_text:
        return 0
    soup = BeautifulSoup(html_or_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    words = re.findall(r"\b\S+\b", text)
    return len(words)

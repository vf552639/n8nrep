import re
from collections import Counter

from bs4 import BeautifulSoup
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.project_content_anchor import ProjectContentAnchor

# Russian and English basic stop words
STOP_WORDS = set(
    [
        "и",
        "в",
        "во",
        "не",
        "что",
        "он",
        "на",
        "я",
        "с",
        "со",
        "как",
        "а",
        "то",
        "все",
        "она",
        "так",
        "его",
        "но",
        "да",
        "ты",
        "к",
        "у",
        "же",
        "вы",
        "за",
        "бы",
        "по",
        "только",
        "ее",
        "мне",
        "было",
        "вот",
        "от",
        "меня",
        "еще",
        "нет",
        "о",
        "из",
        "ему",
        "теперь",
        "когда",
        "даже",
        "ну",
        "вдруг",
        "ли",
        "если",
        "уже",
        "или",
        "ни",
        "быть",
        "был",
        "него",
        "до",
        "вас",
        "нибудь",
        "опять",
        "уж",
        "вам",
        "ведь",
        "там",
        "потом",
        "себя",
        "ничего",
        "ей",
        "может",
        "они",
        "тут",
        "где",
        "есть",
        "надо",
        "ней",
        "для",
        "мы",
        "тебя",
        "их",
        "чем",
        "была",
        "сам",
        "чтоб",
        "без",
        "будто",
        "чего",
        "раз",
        "тоже",
        "себе",
        "под",
        "будет",
        "ж",
        "тогда",
        "кто",
        "этот",
        "того",
        "потому",
        "этого",
        "какой",
        "совсем",
        "ним",
        "здесь",
        "этом",
        "один",
        "почти",
        "мой",
        "тем",
        "чтобы",
        "нее",
        "сейчас",
        "были",
        "куда",
        "зачем",
        "всех",
        "никогда",
        "можно",
        "при",
        "наконец",
        "два",
        "об",
        "другой",
        "хоть",
        "после",
        "над",
        "больше",
        "тот",
        "через",
        "эти",
        "нас",
        "про",
        "всего",
        "них",
        "какая",
        "много",
        "разве",
        "три",
        "эту",
        "моя",
        "впрочем",
        "хорошо",
        "свою",
        "этой",
        "перед",
        "иногда",
        "лучше",
        "чуть",
        "том",
        "нельзя",
        "такой",
        "им",
        "более",
        "всегда",
        "конечно",
        "всю",
        "между",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "were",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "about",
        "as",
        "by",
        "this",
        "that",
        "it",
        "he",
        "she",
        "they",
        "we",
        "you",
        "i",
        "of",
        "from",
    ]
)


class ContentDeduplicator:
    def __init__(self, db: Session):
        self.db = db

    def extract_key_phrases(self, text: str, top_n: int = 20) -> list:
        # Simple tokenization
        words = re.findall(r"\b[a-zA-Zа-яА-ЯёЁ]{3,}\b", text.lower())
        filtered_words = [w for w in words if w not in STOP_WORDS]

        # 2-grams and 3-grams
        phrases = []
        for i in range(len(filtered_words) - 1):
            phrases.append(f"{filtered_words[i]} {filtered_words[i + 1]}")
            if i < len(filtered_words) - 2:
                phrases.append(f"{filtered_words[i]} {filtered_words[i + 1]} {filtered_words[i + 2]}")

        counter = Counter(phrases)
        return [phrase for phrase, count in counter.most_common(top_n)]

    def extract_anchors(self, article_html: str, task_id: str, keyword: str) -> dict:
        if not article_html:
            return {
                "task_id": task_id,
                "keyword": keyword,
                "title": "",
                "h2_headings": [],
                "h3_headings": [],
                "key_phrases": [],
                "first_paragraphs": [],
                "word_count": 0,
            }

        soup = BeautifulSoup(article_html, "html.parser")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

        h2_headings = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]
        h3_headings = [h3.get_text(strip=True) for h3 in soup.find_all("h3")]

        first_paragraphs = []
        for h2 in soup.find_all("h2"):
            # Find the next sibling that is a paragraph
            nxt = h2.find_next_sibling()
            while nxt and nxt.name not in ["h2", "h1"]:
                if nxt.name == "p":
                    para_text = nxt.get_text(strip=True)
                    if para_text:
                        first_paragraphs.append(para_text)
                        break
                nxt = nxt.find_next_sibling()

        # Extract key phrases from the body (paragraphs)
        body_text = " ".join([p.get_text(strip=True) for p in soup.find_all("p")])
        key_phrases = self.extract_key_phrases(body_text)

        word_count = len(re.findall(r"\b\S+\b", soup.get_text()))

        return {
            "task_id": str(task_id),
            "keyword": keyword,
            "title": title,
            "h2_headings": h2_headings,
            "h3_headings": h3_headings,
            "key_phrases": key_phrases,
            "first_paragraphs": first_paragraphs,
            "word_count": word_count,
        }

    def save_anchors(self, project_id: str, task_id: str, anchors: dict):
        anchor_obj = (
            self.db.query(ProjectContentAnchor).filter(ProjectContentAnchor.task_id == task_id).first()
        )

        if anchor_obj:
            anchor_obj.keyword = anchors.get("keyword")
            anchor_obj.title = anchors.get("title")
            anchor_obj.h2_headings = anchors.get("h2_headings", [])
            anchor_obj.h3_headings = anchors.get("h3_headings", [])
            anchor_obj.key_phrases = anchors.get("key_phrases", [])
            anchor_obj.first_paragraphs = anchors.get("first_paragraphs", [])
        else:
            anchor_obj = ProjectContentAnchor(
                project_id=project_id,
                task_id=task_id,
                keyword=anchors.get("keyword"),
                title=anchors.get("title"),
                h2_headings=anchors.get("h2_headings", []),
                h3_headings=anchors.get("h3_headings", []),
                key_phrases=anchors.get("key_phrases", []),
                first_paragraphs=anchors.get("first_paragraphs", []),
            )
            self.db.add(anchor_obj)
        self.db.commit()

    def get_already_covered(self, project_id: str, current_task_id: str) -> str:
        # Get last 20 tasks for the project excluding the current one
        anchors = (
            self.db.query(ProjectContentAnchor)
            .filter(
                ProjectContentAnchor.project_id == project_id, ProjectContentAnchor.task_id != current_task_id
            )
            .order_by(desc(ProjectContentAnchor.created_at))
            .limit(20)
            .all()
        )

        if not anchors:
            return ""

        context_blocks = []
        for anchor in anchors:
            h2_list = " | ".join(anchor.h2_headings[:5]) if anchor.h2_headings else ""
            key_phrases_list = ", ".join(anchor.key_phrases[:5]) if anchor.key_phrases else ""

            block = f'### Страница: "{anchor.keyword}"\n'
            block += f"- H1: {anchor.title}\n"
            if h2_list:
                block += f"- H2: {h2_list}\n"
            if key_phrases_list:
                block += f"- Ключевые тезисы: {key_phrases_list}\n"
            context_blocks.append(block)

        # ~3000 tokens limit. Let's just limit chars for simplicity since 3000 tokens = ~12000 chars
        # We limit to 20 articles config max, which should be well under limits.

        header = "## Уже опубликованные страницы этого проекта (НЕ повторяй эти заголовки и тезисы):\n\n"
        footer = "\n---\nВАЖНО: Каждая новая страница должна раскрывать тему с УНИКАЛЬНОГО ракурса.\nНе повторяй заголовки H2, перечисленные выше.\nЕсли тема пересекается — подойди с другой стороны, используй другие аргументы и примеры."

        result = header + "\n".join(context_blocks) + footer

        return result[:12000]  # Safe crop

from pydantic import BaseModel


class ArticleUpdate(BaseModel):
    html_content: str | None = None
    title: str | None = None
    description: str | None = None

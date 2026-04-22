"""factory_boy factories (bind sqlalchemy_session in integration tests)."""

from __future__ import annotations

import uuid

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.article import GeneratedArticle
from app.models.author import Author
from app.models.blueprint import BlueprintPage, SiteBlueprint
from app.models.project import SiteProject
from app.models.prompt import Prompt
from app.models.site import Site
from app.models.task import Task
from app.models.template import LegalPageTemplate, Template


class SiteFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Site
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"test-site-{n}")
    domain = factory.Sequence(lambda n: f"site{n}.example.com")
    country = "DE"
    language = "De"
    is_active = True


class AuthorFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Author
        sqlalchemy_session_persistence = "flush"

    author = factory.Sequence(lambda n: f"Author {n}")
    country = "DE"
    language = "De"


class BlueprintFactory(SQLAlchemyModelFactory):
    class Meta:
        model = SiteBlueprint
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Blueprint {n}")
    slug = factory.Sequence(lambda n: f"bp-slug-{n}")
    is_active = True


class BlueprintPageFactory(SQLAlchemyModelFactory):
    class Meta:
        model = BlueprintPage
        sqlalchemy_session_persistence = "flush"

    class Params:
        blueprint = factory.SubFactory(BlueprintFactory)

    id = factory.LazyFunction(uuid.uuid4)
    blueprint_id = factory.LazyAttribute(lambda o: o.blueprint.id)
    page_slug = factory.Sequence(lambda n: f"page-{n}")
    page_title = "Page title"
    page_type = "article"
    keyword_template = "{seed}"
    filename = factory.Sequence(lambda n: f"page-{n}.html")
    sort_order = 0
    pipeline_preset = "full"


class ProjectFactory(SQLAlchemyModelFactory):
    class Meta:
        model = SiteProject
        sqlalchemy_session_persistence = "flush"

    class Params:
        blueprint = factory.SubFactory(BlueprintFactory)
        site = factory.SubFactory(SiteFactory)

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"project-{n}")
    blueprint_id = factory.LazyAttribute(lambda o: o.blueprint.id)
    site_id = factory.LazyAttribute(lambda o: o.site.id)
    seed_keyword = "seed"
    country = "DE"
    language = "De"
    status = "pending"
    competitor_urls = factory.LazyFunction(list)


class TemplateFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Template
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"template-{n}")
    html_template = "<html><body>{{content}}</body></html>"
    is_active = True


class LegalPageTemplateFactory(SQLAlchemyModelFactory):
    class Meta:
        model = LegalPageTemplate
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"legal-{n}")
    page_type = "privacy_policy"
    content = "Sample legal text for tests."
    content_format = "text"


class PromptFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Prompt
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    agent_name = factory.Sequence(lambda n: f"test_agent_{n}")
    version = 1
    is_active = True
    skip_in_pipeline = False
    system_prompt = "System prompt for tests."
    user_prompt = "User prompt for tests."
    model = "openai/gpt-4o-mini"


class TaskFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Task
        sqlalchemy_session_persistence = "flush"

    class Params:
        site = factory.SubFactory(SiteFactory)

    id = factory.LazyFunction(uuid.uuid4)
    main_keyword = factory.Sequence(lambda n: f"kw-{n}")
    country = "DE"
    language = "De"
    page_type = "article"
    status = "pending"
    target_site_id = factory.LazyAttribute(lambda o: o.site.id)


class ArticleFactory(SQLAlchemyModelFactory):
    class Meta:
        model = GeneratedArticle
        sqlalchemy_session_persistence = "flush"

    class Params:
        task = factory.SubFactory(TaskFactory)

    id = factory.LazyFunction(uuid.uuid4)
    task_id = factory.LazyAttribute(lambda o: o.task.id)
    title = "Article title"
    html_content = "<p>Hello</p>"

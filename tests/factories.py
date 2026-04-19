"""factory_boy factories (bind sqlalchemy_session in integration tests)."""

from __future__ import annotations

import uuid

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.author import Author
from app.models.site import Site
from app.models.task import Task


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


class TaskFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Task
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    main_keyword = factory.Sequence(lambda n: f"kw-{n}")
    country = "DE"
    language = "De"
    page_type = "article"
    status = "pending"
    target_site = factory.SubFactory(SiteFactory)

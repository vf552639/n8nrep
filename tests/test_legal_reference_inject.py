"""Tests for legal template variables injected into the pipeline context."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.blueprint import BlueprintPage
from app.models.project import SiteProject
from app.models.site import Site
from app.models.template import LegalPageTemplate
from app.services.legal_reference import (
    inject_legal_template_vars,
    page_type_label_for,
)


def test_page_type_label_for_known_and_unknown():
    assert page_type_label_for("privacy_policy") == "Privacy Policy"
    assert page_type_label_for("custom_thing") == "Custom Thing"


def test_inject_legal_no_site_early_defaults():
    tv: dict = {}
    task = SimpleNamespace(
        page_type="privacy_policy",
        project_id=None,
        blueprint_page_id=None,
        target_site_id=uuid.uuid4(),
    )
    ctx = SimpleNamespace(template_vars=tv, use_serp=False, task=task, db=MagicMock())
    ctx.db.query.return_value.filter.return_value.first.return_value = None

    inject_legal_template_vars(ctx)

    assert tv["page_type_label"] == "Privacy Policy"
    assert tv["legal_reference"] == ""
    assert tv["legal_reference_html"] == ""
    assert tv["legal_reference_format"] == "text"
    assert tv["legal_template_notes"] == ""
    assert tv["legal_variables"] == "{}"


def test_inject_legal_with_serp_still_sets_label():
    tv = {}
    task = SimpleNamespace(
        page_type="cookie_policy",
        project_id=None,
        blueprint_page_id=None,
        target_site_id=uuid.uuid4(),
    )
    ctx = SimpleNamespace(template_vars=tv, use_serp=True, task=task, db=MagicMock())

    inject_legal_template_vars(ctx)

    assert tv["page_type_label"] == "Cookie Policy"
    assert tv["legal_reference"] == ""


def test_inject_non_legal_only_defaults():
    tv = {}
    task = SimpleNamespace(
        page_type="article",
        project_id=None,
        blueprint_page_id=None,
        target_site_id=uuid.uuid4(),
    )
    ctx = SimpleNamespace(template_vars=tv, use_serp=False, task=task, db=MagicMock())

    inject_legal_template_vars(ctx)

    assert "page_type_label" not in tv
    assert tv["legal_reference"] == ""


def test_inject_legal_with_template_text_format():
    tv = {}
    site_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    tpl_id = uuid.uuid4()
    task = SimpleNamespace(
        page_type="privacy_policy",
        project_id=proj_id,
        blueprint_page_id=None,
        target_site_id=site_id,
    )

    site = SimpleNamespace(legal_info={"company_name": "Acme Ltd"})
    project = SimpleNamespace(legal_template_map={"privacy_policy": str(tpl_id)})
    lp = SimpleNamespace(
        content="Hello {{company_name}}",
        content_format="TEXT",
        notes="Note A",
        variables={"extra": "x"},
        page_type="privacy_policy",
    )

    def query_side_effect(model):
        q = MagicMock()
        if model is Site:
            q.filter.return_value.first.return_value = site
        elif model is SiteProject:
            q.filter.return_value.first.return_value = project
        elif model is LegalPageTemplate:
            q.filter.return_value.first.return_value = lp
        else:
            q.filter.return_value.first.return_value = None
        return q

    ctx = SimpleNamespace(template_vars=tv, use_serp=False, task=task, db=MagicMock())
    ctx.db.query.side_effect = query_side_effect

    inject_legal_template_vars(ctx)

    assert tv["page_type_label"] == "Privacy Policy"
    assert tv["legal_reference"] == "Hello Acme Ltd"
    assert tv["legal_reference_html"] == "Hello Acme Ltd"
    assert tv["legal_reference_format"] == "text"
    assert tv["legal_template_notes"] == "Note A"
    merged = json.loads(tv["legal_variables"])
    assert merged["company_name"] == "Acme Ltd"
    assert merged["extra"] == "x"


def test_inject_invalid_content_format_falls_back_to_text():
    tv = {}
    site_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    tpl_id = uuid.uuid4()
    task = SimpleNamespace(
        page_type="privacy_policy",
        project_id=proj_id,
        blueprint_page_id=None,
        target_site_id=site_id,
    )
    site = SimpleNamespace(legal_info={})
    project = SimpleNamespace(legal_template_map={"privacy_policy": str(tpl_id)})
    lp = SimpleNamespace(
        content="x",
        content_format="markdown",
        notes=None,
        variables={},
        page_type="privacy_policy",
    )

    def query_side_effect(model):
        q = MagicMock()
        if model is Site:
            q.filter.return_value.first.return_value = site
        elif model is SiteProject:
            q.filter.return_value.first.return_value = project
        elif model is LegalPageTemplate:
            q.filter.return_value.first.return_value = lp
        else:
            q.filter.return_value.first.return_value = None
        return q

    ctx = SimpleNamespace(template_vars=tv, use_serp=False, task=task, db=MagicMock())
    ctx.db.query.side_effect = query_side_effect

    inject_legal_template_vars(ctx)

    assert tv["legal_reference_format"] == "text"


def test_inject_blueprint_default_template():
    tv = {}
    site_id = uuid.uuid4()
    bp_page_id = uuid.uuid4()
    tpl_id = uuid.uuid4()
    task = SimpleNamespace(
        page_type="privacy_policy",
        project_id=None,
        blueprint_page_id=bp_page_id,
        target_site_id=site_id,
    )
    site = SimpleNamespace(legal_info={})
    bp = SimpleNamespace(default_legal_template_id=tpl_id)
    lp = SimpleNamespace(
        content="Body",
        content_format="html",
        notes="",
        variables={},
        page_type="privacy_policy",
    )

    def query_side_effect(model):
        q = MagicMock()
        if model is Site:
            q.filter.return_value.first.return_value = site
        elif model is BlueprintPage:
            q.filter.return_value.first.return_value = bp
        elif model is LegalPageTemplate:
            q.filter.return_value.first.return_value = lp
        else:
            q.filter.return_value.first.return_value = None
        return q

    ctx = SimpleNamespace(template_vars=tv, use_serp=False, task=task, db=MagicMock())
    ctx.db.query.side_effect = query_side_effect

    inject_legal_template_vars(ctx)

    assert tv["legal_reference"] == "Body"
    assert tv["legal_reference_format"] == "html"

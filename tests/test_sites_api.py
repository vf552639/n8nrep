"""Contract tests for GET /api/sites payload shape (template_id for use_site_template UI)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.api.sites import _site_out


def test_site_out_includes_template_id_and_name_when_linked():
    db = MagicMock()
    tpl_id = uuid.uuid4()
    site = MagicMock()
    site.id = uuid.uuid4()
    site.name = "Casino DE"
    site.domain = "example.com"
    site.country = "DE"
    site.language = "de"
    site.is_active = True
    site.template_id = tpl_id
    site.legal_info = {"company_name": "ACME"}

    tpl = MagicMock()
    tpl.name = "Main layout"

    q = db.query.return_value
    q.filter.return_value.first.return_value = tpl

    out = _site_out(site, db)

    assert out["template_id"] == str(tpl_id)
    assert out["template_name"] == "Main layout"
    assert out["has_template"] is True
    assert out["legal_info"] == {"company_name": "ACME"}


def test_site_out_null_template_when_no_template_id():
    db = MagicMock()
    site = MagicMock()
    site.id = uuid.uuid4()
    site.name = "Plain"
    site.domain = "plain.example"
    site.country = "US"
    site.language = "en"
    site.is_active = True
    site.template_id = None
    site.legal_info = None

    out = _site_out(site, db)

    assert out["template_id"] is None
    assert out["template_name"] is None
    assert out["has_template"] is False
    assert out["legal_info"] == {}

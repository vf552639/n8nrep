"""legal_page_templates refactor (name, content, content_format); site_projects.legal_template_map; normalize country strings

Revision ID: n1o2p3q4r5sa
Revises: m9n0o1p2q3re
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "n1o2p3q4r5sa"
down_revision: Union[str, Sequence[str], None] = "m9n0o1p2q3re"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "legal_page_templates",
        sa.Column("name", sa.String(length=200), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE legal_page_templates SET name = country || ' — ' || page_type "
            "WHERE name IS NULL"
        )
    )
    op.alter_column("legal_page_templates", "name", existing_type=sa.String(length=200), nullable=False)

    op.add_column(
        "legal_page_templates",
        sa.Column(
            "content_format",
            sa.String(length=10),
            nullable=False,
            server_default="html",
        ),
    )

    op.alter_column(
        "legal_page_templates",
        "html_content",
        new_column_name="content",
        existing_type=sa.Text(),
        existing_nullable=False,
    )

    op.drop_constraint(
        "uq_legal_page_templates_country_page_type",
        "legal_page_templates",
        type_="unique",
    )
    op.drop_column("legal_page_templates", "country")

    op.create_unique_constraint(
        "uq_legal_tpl_name_page_type",
        "legal_page_templates",
        ["name", "page_type"],
    )

    op.alter_column(
        "legal_page_templates",
        "content_format",
        existing_type=sa.String(length=10),
        existing_nullable=False,
        server_default="text",
    )

    op.add_column(
        "site_projects",
        sa.Column(
            "legal_template_map",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Optional: normalize legacy country spellings (Part 6.3)
    for stmt in (
        "UPDATE authors SET country = 'FR' WHERE UPPER(TRIM(country)) IN ('FRANCE', 'FRENCH')",
        "UPDATE authors SET country = 'DE' WHERE UPPER(TRIM(country)) IN ('GERMANY', 'GERMAN', 'DEUTSCHLAND')",
        "UPDATE authors SET country = 'GB' WHERE UPPER(TRIM(country)) IN ('GREAT BRITAIN', 'UK', 'UNITED KINGDOM', 'ENGLAND')",
        "UPDATE authors SET country = 'AU' WHERE UPPER(TRIM(country)) IN ('AUSTRALIA', 'AUSTRALIAN')",
        "UPDATE authors SET country = 'BE' WHERE UPPER(TRIM(country)) IN ('BELGIUM', 'BELGIAN')",
        "UPDATE authors SET country = 'CA' WHERE UPPER(TRIM(country)) IN ('CANADA', 'CANADIAN')",
        "UPDATE authors SET country = 'DK' WHERE UPPER(TRIM(country)) IN ('DENMARK', 'DANISH')",
        "UPDATE authors SET country = 'PL' WHERE UPPER(TRIM(country)) IN ('POLAND', 'POLISH')",
        "UPDATE authors SET country = UPPER(TRIM(country)) WHERE country IS NOT NULL AND LENGTH(TRIM(country)) = 2",
        "UPDATE sites SET country = 'FR' WHERE UPPER(TRIM(country)) IN ('FRANCE', 'FRENCH')",
        "UPDATE sites SET country = 'DE' WHERE UPPER(TRIM(country)) IN ('GERMANY', 'GERMAN', 'DEUTSCHLAND')",
        "UPDATE sites SET country = 'GB' WHERE UPPER(TRIM(country)) IN ('GREAT BRITAIN', 'UK', 'UNITED KINGDOM', 'ENGLAND')",
        "UPDATE sites SET country = 'AU' WHERE UPPER(TRIM(country)) IN ('AUSTRALIA', 'AUSTRALIAN')",
        "UPDATE sites SET country = 'BE' WHERE UPPER(TRIM(country)) IN ('BELGIUM', 'BELGIAN')",
        "UPDATE sites SET country = 'CA' WHERE UPPER(TRIM(country)) IN ('CANADA', 'CANADIAN')",
        "UPDATE sites SET country = 'DK' WHERE UPPER(TRIM(country)) IN ('DENMARK', 'DANISH')",
        "UPDATE sites SET country = 'PL' WHERE UPPER(TRIM(country)) IN ('POLAND', 'POLISH')",
        "UPDATE sites SET country = UPPER(TRIM(country)) WHERE country IS NOT NULL AND LENGTH(TRIM(country)) = 2",
    ):
        op.execute(sa.text(stmt))


def downgrade() -> None:
    op.drop_column("site_projects", "legal_template_map")

    op.drop_constraint("uq_legal_tpl_name_page_type", "legal_page_templates", type_="unique")
    op.add_column(
        "legal_page_templates",
        sa.Column("country", sa.String(length=10), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE legal_page_templates SET country = SPLIT_PART(name, ' — ', 1) "
            "WHERE name LIKE '% — %'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE legal_page_templates SET country = 'XX' WHERE country IS NULL OR country = ''"
        )
    )
    op.alter_column("legal_page_templates", "country", existing_type=sa.String(length=10), nullable=False)

    op.alter_column(
        "legal_page_templates",
        "content",
        new_column_name="html_content",
        existing_type=sa.Text(),
        existing_nullable=False,
    )

    op.drop_column("legal_page_templates", "content_format")
    op.drop_column("legal_page_templates", "name")

    op.create_unique_constraint(
        "uq_legal_page_templates_country_page_type",
        "legal_page_templates",
        ["country", "page_type"],
    )

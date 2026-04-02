"""templates table, legal_page_templates, site.template_id and legal_info; migrate from site_templates

Revision ID: i3d4e5f6a7b8
Revises: h4c5d6e7f9a1
Create Date: 2026-04-01 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid as uuid_lib

revision = "i3d4e5f6a7b8"
down_revision = "h4c5d6e7f9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("html_template", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preview_screenshot", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "legal_page_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country", sa.String(length=10), nullable=False),
        sa.Column("page_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column(
            "variables",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country", "page_type", name="uq_legal_page_templates_country_page_type"),
    )

    op.add_column(
        "sites",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("legal_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_sites_template_id_templates",
        "sites",
        "templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_sites_template_id"), "sites", ["template_id"], unique=False)

    # --- Data: site_templates -> templates + sites.template_id ---
    conn = op.get_bind()
    from sqlalchemy import text

    rows = conn.execute(
        text(
            """
            SELECT id, site_id, template_name, html_template, is_active
            FROM site_templates
            ORDER BY site_id, id
            """
        )
    ).fetchall()

    html_to_tid: dict[str, str] = {}
    for r in rows:
        html = r.html_template
        if html not in html_to_tid:
            tid = str(uuid_lib.uuid4())
            active = bool(r.is_active) if r.is_active is not None else True
            conn.execute(
                text(
                    """
                    INSERT INTO templates (id, name, html_template, description, preview_screenshot, is_active, created_at, updated_at)
                    VALUES (:id, :name, :html, NULL, NULL, :active, NOW(), NOW())
                    """
                ),
                {"id": tid, "name": r.template_name, "html": html, "active": active},
            )
            html_to_tid[html] = tid

    sites_seen: set[str] = set()
    for r in rows:
        sid = str(r.site_id)
        if sid in sites_seen:
            continue
        tid = html_to_tid[r.html_template]
        conn.execute(
            text("UPDATE sites SET template_id = CAST(:tid AS uuid) WHERE id = CAST(:sid AS uuid)"),
            {"tid": tid, "sid": sid},
        )
        sites_seen.add(sid)

    op.drop_table("site_templates")


def downgrade() -> None:
    op.drop_constraint("fk_sites_template_id_templates", "sites", type_="foreignkey")
    op.drop_index(op.f("ix_sites_template_id"), table_name="sites")
    op.drop_column("sites", "legal_info")
    op.drop_column("sites", "template_id")

    op.drop_table("legal_page_templates")
    op.drop_table("templates")

    op.create_table(
        "site_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("html_template", sa.Text(), nullable=False),
        sa.Column("pages_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

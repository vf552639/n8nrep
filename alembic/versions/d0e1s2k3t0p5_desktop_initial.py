"""desktop: initial schema (all tables, SQLite-compatible)

Revision ID: d0e1s2k3t0p5
Revises: (none)
Create Date: 2026-05-11

"""

from alembic import op
import sqlalchemy as sa

revision = "d0e1s2k3t0p5"
down_revision = None
branch_labels = ["desktop"]
depends_on = None


def upgrade() -> None:
    # authors
    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("country_full", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("co_short", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("imitation", sa.Text(), nullable=True),
        sa.Column("year", sa.String(50), nullable=True),
        sa.Column("face", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("rhythms_style", sa.Text(), nullable=True),
        sa.Column("exclude_words", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # templates
    op.create_table(
        "templates",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("html_template", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preview_screenshot", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # legal_page_templates
    op.create_table(
        "legal_page_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("page_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(10), nullable=False, server_default="text"),
        sa.Column("variables", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "page_type", name="uq_legal_tpl_name_page_type"),
    )

    # sites
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(200), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("template_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("legal_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sites_template_id", "sites", ["template_id"])

    # site_blueprints
    op.create_table(
        "site_blueprints",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # blueprint_pages
    op.create_table(
        "blueprint_pages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("page_slug", sa.String(100), nullable=False),
        sa.Column("page_title", sa.String(300), nullable=False),
        sa.Column("page_type", sa.String(50), nullable=False, server_default="article"),
        sa.Column("keyword_template", sa.String(500), nullable=False),
        sa.Column("keyword_template_brand", sa.String(500), nullable=True),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nav_label", sa.String(100), nullable=True),
        sa.Column("show_in_nav", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("show_in_footer", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("hide_author_geo", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("use_serp", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("pipeline_preset", sa.String(20), nullable=False, server_default="full"),
        sa.Column("pipeline_steps_custom", sa.JSON(), nullable=True),
        sa.Column("default_legal_template_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["site_blueprints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["default_legal_template_id"], ["legal_page_templates.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # prompts
    op.create_table(
        "prompts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("skip_in_pipeline", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("max_tokens_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("temperature", sa.Float(), nullable=True, server_default="0.7"),
        sa.Column("temperature_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("frequency_penalty", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("frequency_penalty_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("presence_penalty", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("presence_penalty_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("top_p", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("top_p_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompts_agent_name", "prompts", ["agent_name"])
    op.create_index("ix_prompts_is_active", "prompts", ["is_active"])

    # site_projects
    op.create_table(
        "site_projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("site_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("seed_keyword", sa.String(500), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("target_site", sa.String(500), nullable=True),
        sa.Column("seed_is_brand", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="pending"),
        sa.Column("current_page_index", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("stopping_requested", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("build_zip_url", sa.Text(), nullable=True),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("generation_started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("log_events", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("serp_config", sa.JSON(), nullable=True),
        sa.Column("project_keywords", sa.JSON(), nullable=True),
        sa.Column("legal_template_map", sa.JSON(), nullable=True),
        sa.Column("use_site_template", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("competitor_urls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"]),
        sa.ForeignKeyConstraint(["blueprint_id"], ["site_blueprints.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("main_keyword", sa.String(500), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("page_type", sa.String(50), nullable=False, server_default="article"),
        sa.Column("target_site_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_cost", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("serp_data", sa.JSON(), nullable=True),
        sa.Column("competitors_text", sa.Text(), nullable=True),
        sa.Column("outline", sa.JSON(), nullable=True),
        sa.Column("additional_keywords", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("step_results", sa.JSON(), nullable=True),
        sa.Column("serp_config", sa.JSON(), nullable=True),
        sa.Column("log_events", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(), nullable=True),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("blueprint_page_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"]),
        sa.ForeignKeyConstraint(["blueprint_page_id"], ["blueprint_pages.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["site_projects.id"]),
        sa.ForeignKeyConstraint(["target_site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_target_site_id", "tasks", ["target_site_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"])

    # generated_articles
    op.create_table(
        "generated_articles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("full_page_html", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("fact_check_status", sa.String(20), nullable=True, server_default=""),
        sa.Column("fact_check_issues", sa.JSON(), nullable=True),
        sa.Column("fact_check_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("needs_review", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # project_content_anchors
    op.create_table(
        "project_content_anchors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("keyword", sa.String(500), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("h2_headings", sa.JSON(), nullable=True),
        sa.Column("h3_headings", sa.JSON(), nullable=True),
        sa.Column("key_phrases", sa.JSON(), nullable=True),
        sa.Column("first_paragraphs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["site_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(
        "ix_project_content_anchors_project_id", "project_content_anchors", ["project_id"]
    )


def downgrade() -> None:
    op.drop_table("project_content_anchors")
    op.drop_table("generated_articles")
    op.drop_table("tasks")
    op.drop_table("site_projects")
    op.drop_table("prompts")
    op.drop_table("blueprint_pages")
    op.drop_table("site_blueprints")
    op.drop_table("sites")
    op.drop_table("legal_page_templates")
    op.drop_table("templates")
    op.drop_table("authors")

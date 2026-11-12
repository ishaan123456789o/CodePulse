"""Indexed PostgreSQL full-text and name prefix search."""

from alembic import op

revision = "0002_search_indexes"
down_revision = "52027e09a5a9"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_repositories_search ON repositories USING gin (to_tsvector('simple', coalesce(full_name, '') || ' ' || coalesce(description, '')))"
        )
        op.execute(
            "CREATE INDEX ix_repositories_name_prefix ON repositories (lower(full_name) text_pattern_ops)"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_repositories_name_prefix", table_name="repositories")
        op.drop_index("ix_repositories_search", table_name="repositories")

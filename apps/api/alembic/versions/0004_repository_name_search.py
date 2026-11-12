"""Tokenize repository names independently from the owner/name slash."""

from alembic import op

revision = "0004_repository_name_search"
down_revision = "0003_optional_activity"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_repositories_search", table_name="repositories")
        op.execute(
            "CREATE INDEX ix_repositories_search ON repositories USING gin (to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '')))"
        )
        op.execute(
            "CREATE INDEX ix_repositories_short_name_prefix ON repositories (lower(name) text_pattern_ops)"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_repositories_short_name_prefix", table_name="repositories")
        op.drop_index("ix_repositories_search", table_name="repositories")
        op.execute(
            "CREATE INDEX ix_repositories_search ON repositories USING gin (to_tsvector('simple', coalesce(full_name, '') || ' ' || coalesce(description, '')))"
        )

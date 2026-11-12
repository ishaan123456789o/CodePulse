"""Track freshness of optional activity separately from metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0003_optional_activity"
down_revision = "0002_search_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "repositories", sa.Column("activity_fetched_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("repositories", "activity_fetched_at")

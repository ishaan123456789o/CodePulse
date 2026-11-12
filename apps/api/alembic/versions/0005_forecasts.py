"""Persist prospective forecasts separately from measured momentum."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_forecasts"
down_revision = "0004_repository_name_search"
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "repository_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *[
            sa.Column(name, sa.DateTime(timezone=True), nullable=False)
            for name in ("forecast_day", "issued_at", "as_of", "target_at")
        ],
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("demo", sa.Boolean(), nullable=False),
        sa.Column("stars_at_origin", sa.Integer(), nullable=False),
        sa.Column("projected_growth", sa.Float(), nullable=False),
        sa.Column("baseline_growth", sa.Float(), nullable=False),
        sa.Column("breakout_threshold", sa.Integer(), nullable=False),
        sa.Column("breakout_ratio", sa.Float(), nullable=False),
        sa.Column("predicted_breakout", sa.Boolean(), nullable=False),
        sa.Column("features", json_type, nullable=False),
        sa.Column("explanation", json_type, nullable=False),
        sa.Column("realized_growth", sa.Float()),
        sa.Column("actual_breakout", sa.Boolean()),
        sa.Column("outcome_at", sa.DateTime(timezone=True)),
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
        sa.Column("evaluation_status", sa.String(30), nullable=False),
        sa.UniqueConstraint("repository_id", "forecast_day", "model_version"),
    )
    op.create_index(
        "ix_forecast_repo_issued", "repository_forecasts", ["repository_id", "issued_at"]
    )
    op.create_index("ix_forecast_due", "repository_forecasts", ["target_at", "evaluated_at"])


def downgrade():
    op.drop_table("repository_forecasts")

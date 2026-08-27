"""Initial appointments schema with overlap protection.

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


appointment_status = postgresql.ENUM(
    "booked", "confirmed", "cancelled", name="appointment_status", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE TYPE appointment_status AS ENUM ('booked', 'confirmed', 'cancelled')")

    op.create_table(
        "specialists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False, unique=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("specialist_active_name_idx", "specialists", ["active", "name"])

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("duration_minutes > 0", name="service_duration_positive"),
        sa.CheckConstraint("price >= 0", name="service_price_nonnegative"),
        sa.UniqueConstraint("specialist_id", "name", name="service_specialist_name_uniq"),
    )
    op.create_index("ix_services_specialist_id", "services", ["specialist_id"])
    op.create_index("service_active_specialist_idx", "services", ["active", "specialist_id"])

    op.create_table(
        "availability_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="availability_weekday_range"),
        sa.CheckConstraint("start_time < end_time", name="availability_time_order"),
        sa.CheckConstraint(
            "ends_on IS NULL OR starts_on IS NULL OR starts_on <= ends_on",
            name="availability_date_order",
        ),
        sa.UniqueConstraint(
            "specialist_id",
            "weekday",
            "start_time",
            "end_time",
            "starts_on",
            name="availability_rule_uniq",
        ),
    )
    op.create_index("ix_availability_rules_specialist_id", "availability_rules", ["specialist_id"])
    op.create_index(
        "availability_lookup_idx", "availability_rules", ["specialist_id", "weekday", "active"]
    )

    op.create_table(
        "availability_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.CheckConstraint(
            "(available = false AND start_time IS NULL AND end_time IS NULL) OR "
            "(available = true AND start_time IS NOT NULL "
            "AND end_time IS NOT NULL AND start_time < end_time)",
            name="availability_exception_window_valid",
        ),
        sa.UniqueConstraint(
            "specialist_id", "exception_date", name="availability_exception_date_uniq"
        ),
    )
    op.create_index(
        "ix_availability_exceptions_specialist_id", "availability_exceptions", ["specialist_id"]
    )
    op.create_index(
        "availability_exception_lookup_idx",
        "availability_exceptions",
        ["specialist_id", "exception_date"],
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("specialists.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("customer_email", sa.String(length=254), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="booked"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("starts_at < ends_at", name="appointment_time_order"),
    )
    op.create_index(
        "appointment_specialist_start_idx", "appointments", ["specialist_id", "starts_at"]
    )
    op.create_index("appointment_customer_email_idx", "appointments", ["customer_email"])
    op.create_index(
        "appointment_active_time_idx",
        "appointments",
        ["specialist_id", "starts_at"],
        postgresql_where=sa.text("status IN ('booked', 'confirmed')"),
    )
    op.execute(
        "ALTER TABLE appointments ADD CONSTRAINT appointment_no_active_overlap "
        "EXCLUDE USING gist "
        "(specialist_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) "
        "WHERE (status IN ('booked', 'confirmed'))"
    )


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("availability_exceptions")
    op.drop_table("availability_rules")
    op.drop_table("services")
    op.drop_table("specialists")
    op.execute("DROP TYPE appointment_status")

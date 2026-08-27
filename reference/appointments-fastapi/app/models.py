import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Specialist(Base):
    __tablename__ = "specialists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    services: Mapped[list["Service"]] = relationship(
        back_populates="specialist", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("specialist_active_name_idx", "active", "name"),)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialists.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    specialist: Mapped[Specialist] = relationship(back_populates="services")

    __table_args__ = (
        UniqueConstraint("specialist_id", "name", name="service_specialist_name_uniq"),
        CheckConstraint("duration_minutes > 0", name="service_duration_positive"),
        CheckConstraint("price >= 0", name="service_price_nonnegative"),
        Index("service_active_specialist_idx", "active", "specialist_id"),
    )


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialists.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="availability_weekday_range"),
        CheckConstraint("start_time < end_time", name="availability_time_order"),
        CheckConstraint(
            "ends_on IS NULL OR starts_on IS NULL OR starts_on <= ends_on",
            name="availability_date_order",
        ),
        UniqueConstraint(
            "specialist_id",
            "weekday",
            "start_time",
            "end_time",
            "starts_on",
            name="availability_rule_uniq",
        ),
        Index("availability_lookup_idx", "specialist_id", "weekday", "active"),
    )


class AvailabilityException(Base):
    __tablename__ = "availability_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialists.id", ondelete="CASCADE"), index=True
    )
    exception_date: Mapped[date] = mapped_column(Date)
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason: Mapped[str] = mapped_column(String(255), default="")

    __table_args__ = (
        UniqueConstraint(
            "specialist_id", "exception_date", name="availability_exception_date_uniq"
        ),
        CheckConstraint(
            "(available = false AND start_time IS NULL AND end_time IS NULL) OR "
            "(available = true AND start_time IS NOT NULL "
            "AND end_time IS NOT NULL AND start_time < end_time)",
            name="availability_exception_window_valid",
        ),
        Index("availability_exception_lookup_idx", "specialist_id", "exception_date"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialists.id", ondelete="RESTRICT")
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT")
    )
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_email: Mapped[str] = mapped_column(String(254))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=AppointmentStatus.BOOKED,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    specialist: Mapped[Specialist] = relationship()
    service: Mapped[Service] = relationship()

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="appointment_time_order"),
        Index("appointment_specialist_start_idx", "specialist_id", "starts_at"),
        Index("appointment_customer_email_idx", "customer_email"),
        Index(
            "appointment_active_time_idx",
            "specialist_id",
            "starts_at",
            postgresql_where=text("status IN ('booked', 'confirmed')"),
        ),
        ExcludeConstraint(
            ("specialist_id", "="),
            (func.tstzrange(starts_at, ends_at, "[)"), "&&"),
            where=text("status IN ('booked', 'confirmed')"),
            using="gist",
            name="appointment_no_active_overlap",
        ),
    )

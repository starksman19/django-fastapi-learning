import hashlib
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import (
    Appointment,
    AppointmentStatus,
    AvailabilityException,
    AvailabilityRule,
    Service,
    Specialist,
)
from app.schemas import AppointmentCreate, SlotRead


logger = logging.getLogger(__name__)
ACTIVE_STATUSES = (AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED)


def _request_hash(payload: AppointmentCreate) -> str:
    normalized = {
        "specialist_id": str(payload.specialist_id),
        "service_id": str(payload.service_id),
        "customer_name": payload.customer_name,
        "customer_email": str(payload.customer_email).lower(),
        "starts_at": payload.starts_at.astimezone(UTC).isoformat(),
    }
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _advisory_lock(session: Session, key: str) -> None:
    lock_id = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big", signed=True)
    session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})


def _availability_windows(session: Session, specialist_id: uuid.UUID, day: date):
    exception = session.scalar(
        select(AvailabilityException).where(
            AvailabilityException.specialist_id == specialist_id,
            AvailabilityException.exception_date == day,
        )
    )
    if exception is not None:
        if not exception.available:
            return []
        return [(exception.start_time, exception.end_time)]

    rules = session.scalars(
        select(AvailabilityRule).where(
            AvailabilityRule.specialist_id == specialist_id,
            AvailabilityRule.weekday == day.weekday(),
            AvailabilityRule.active.is_(True),
            (AvailabilityRule.starts_on.is_(None) | (AvailabilityRule.starts_on <= day)),
            (AvailabilityRule.ends_on.is_(None) | (AvailabilityRule.ends_on >= day)),
        )
    ).all()
    return [(rule.start_time, rule.end_time) for rule in rules]


def _assert_available(
    session: Session,
    specialist: Specialist,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    timezone = ZoneInfo(specialist.timezone)
    local_start = starts_at.astimezone(timezone)
    local_end = ends_at.astimezone(timezone)
    if local_start.date() != local_end.date():
        raise DomainError(
            409, "outside_availability", "Wizyta nie może przechodzić na kolejny dzień."
        )

    windows = _availability_windows(session, specialist.id, local_start.date())
    if not any(
        start_time <= local_start.time().replace(tzinfo=None)
        and local_end.time().replace(tzinfo=None) <= end_time
        for start_time, end_time in windows
    ):
        raise DomainError(
            409, "outside_availability", "Termin znajduje się poza dostępnością specjalisty."
        )


def create_appointment(
    session: Session,
    payload: AppointmentCreate,
    idempotency_key: str,
) -> tuple[Appointment, bool]:
    request_hash = _request_hash(payload)
    try:
        with session.begin():
            _advisory_lock(session, idempotency_key)
            existing = session.scalar(
                select(Appointment).where(Appointment.idempotency_key == idempotency_key)
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise DomainError(
                        409,
                        "idempotency_key_reused",
                        "Ten klucz idempotencji został użyty z innym żądaniem.",
                    )
                return existing, True

            specialist = session.get(Specialist, payload.specialist_id)
            service = session.get(Service, payload.service_id)
            if specialist is None or service is None:
                raise DomainError(404, "not_found", "Nie znaleziono specjalisty lub usługi.")
            if (
                not specialist.active
                or not service.active
                or service.specialist_id != specialist.id
            ):
                raise DomainError(
                    409, "service_unavailable", "Usługa nie jest dostępna u tego specjalisty."
                )

            starts_at = payload.starts_at.astimezone(UTC)
            if starts_at <= datetime.now(UTC):
                raise DomainError(
                    409, "appointment_in_past", "Nie można zarezerwować terminu w przeszłości."
                )
            ends_at = starts_at + timedelta(minutes=service.duration_minutes)
            _assert_available(session, specialist, starts_at, ends_at)

            overlap = session.scalar(
                select(Appointment.id)
                .where(
                    Appointment.specialist_id == specialist.id,
                    Appointment.status.in_(ACTIVE_STATUSES),
                    Appointment.starts_at < ends_at,
                    Appointment.ends_at > starts_at,
                )
                .limit(1)
            )
            if overlap is not None:
                raise DomainError(409, "slot_unavailable", "Wybrany termin jest już zajęty.")

            appointment = Appointment(
                specialist_id=specialist.id,
                service_id=service.id,
                customer_name=payload.customer_name,
                customer_email=str(payload.customer_email),
                starts_at=starts_at,
                ends_at=ends_at,
                status=AppointmentStatus.BOOKED,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            session.add(appointment)
            session.flush()
        return appointment, False
    except IntegrityError as exc:
        session.rollback()
        constraint_name = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint_name, "constraint_name", None)
        if constraint_name == "appointment_no_active_overlap":
            raise DomainError(409, "slot_unavailable", "Wybrany termin jest już zajęty.") from exc
        if constraint_name == "appointments_idempotency_key_key":
            raise DomainError(409, "idempotency_conflict", "Konflikt klucza idempotencji.") from exc
        raise


def change_appointment_status(
    session: Session,
    appointment_id: uuid.UUID,
    target: AppointmentStatus,
) -> Appointment:
    with session.begin():
        appointment = session.scalar(
            select(Appointment).where(Appointment.id == appointment_id).with_for_update()
        )
        if appointment is None:
            raise DomainError(404, "not_found", "Nie znaleziono wizyty.")
        if appointment.status == target:
            return appointment
        allowed = {
            AppointmentStatus.BOOKED: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
            AppointmentStatus.CONFIRMED: {AppointmentStatus.CANCELLED},
            AppointmentStatus.CANCELLED: set(),
        }
        if target not in allowed[appointment.status]:
            raise DomainError(
                409, "invalid_appointment_transition", "Niedozwolona zmiana statusu wizyty."
            )
        appointment.status = target
        session.flush()
    return appointment


def available_slots(session: Session, service_id: uuid.UUID, day: date) -> list[SlotRead]:
    service = session.get(Service, service_id)
    if service is None or not service.active:
        raise DomainError(404, "not_found", "Nie znaleziono aktywnej usługi.")
    specialist = session.get(Specialist, service.specialist_id)
    if specialist is None or not specialist.active:
        raise DomainError(404, "not_found", "Nie znaleziono aktywnego specjalisty.")

    timezone = ZoneInfo(specialist.timezone)
    windows = _availability_windows(session, specialist.id, day)
    if not windows:
        return []

    day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone).astimezone(UTC)
    day_end = datetime.combine(
        day + timedelta(days=1), datetime.min.time(), tzinfo=timezone
    ).astimezone(UTC)
    appointments = session.scalars(
        select(Appointment).where(
            Appointment.specialist_id == specialist.id,
            Appointment.status.in_(ACTIVE_STATUSES),
            Appointment.starts_at < day_end,
            Appointment.ends_at > day_start,
        )
    ).all()

    result: list[SlotRead] = []
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=15)
    now = datetime.now(UTC)
    for start_time, end_time in windows:
        candidate = datetime.combine(day, start_time, tzinfo=timezone)
        window_end = datetime.combine(day, end_time, tzinfo=timezone)
        while candidate + duration <= window_end:
            candidate_utc = candidate.astimezone(UTC)
            candidate_end = (candidate + duration).astimezone(UTC)
            overlaps = any(
                appointment.starts_at < candidate_end and appointment.ends_at > candidate_utc
                for appointment in appointments
            )
            if candidate_utc > now and not overlaps:
                result.append(SlotRead(starts_at=candidate_utc, ends_at=candidate_end))
            candidate += step
    return result


def notify_booking_created(appointment_id: uuid.UUID) -> None:
    logger.info("Appointment %s created; notification would be dispatched here.", appointment_id)

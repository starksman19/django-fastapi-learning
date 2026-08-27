import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.errors import DomainError
from app.models import Appointment, AppointmentStatus
from app.schemas import AppointmentCreate, AppointmentRead, Page, SlotRead
from app.security import require_api_key
from app.services import (
    available_slots,
    change_appointment_status,
    create_appointment,
    notify_booking_created,
)


router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


@router.get("/available-slots", response_model=list[SlotRead])
def list_available_slots(
    service_id: uuid.UUID,
    day: date,
    session: Session = Depends(get_session),
):
    return available_slots(session, service_id, day)


@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentCreate,
    response: Response,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
):
    if not idempotency_key:
        raise DomainError(
            400, "idempotency_key_required", "Nagłówek Idempotency-Key jest wymagany."
        )
    appointment, replayed = create_appointment(session, payload, idempotency_key)
    response.headers["Idempotency-Replayed"] = str(replayed).lower()
    if not replayed:
        background_tasks.add_task(notify_booking_created, appointment.id)
    return appointment


@router.get("/appointments", response_model=Page[AppointmentRead])
def list_appointments(
    specialist_id: uuid.UUID | None = None,
    appointment_status: AppointmentStatus | None = Query(default=None, alias="status"),
    customer_email: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(Appointment)
    if specialist_id:
        statement = statement.where(Appointment.specialist_id == specialist_id)
    if appointment_status:
        statement = statement.where(Appointment.status == appointment_status)
    if customer_email:
        statement = statement.where(Appointment.customer_email == customer_email)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    items = session.scalars(
        statement.order_by(Appointment.starts_at.desc()).offset(offset).limit(limit)
    ).all()
    return Page(items=list(items), total=total or 0, offset=offset, limit=limit)


@router.get("/appointments/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: uuid.UUID, session: Session = Depends(get_session)):
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise DomainError(404, "not_found", "Nie znaleziono wizyty.")
    return appointment


@router.post("/appointments/{appointment_id}/confirm", response_model=AppointmentRead)
def confirm_appointment(appointment_id: uuid.UUID, session: Session = Depends(get_session)):
    return change_appointment_status(session, appointment_id, AppointmentStatus.CONFIRMED)


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(appointment_id: uuid.UUID, session: Session = Depends(get_session)):
    return change_appointment_status(session, appointment_id, AppointmentStatus.CANCELLED)

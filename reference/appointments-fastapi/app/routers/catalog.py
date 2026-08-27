import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.errors import DomainError
from app.models import AvailabilityException, AvailabilityRule, Service, Specialist
from app.schemas import (
    AvailabilityExceptionCreate,
    AvailabilityExceptionRead,
    AvailabilityRuleCreate,
    AvailabilityRuleRead,
    Page,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    SpecialistCreate,
    SpecialistRead,
    SpecialistUpdate,
)
from app.security import require_api_key


router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def get_or_404(session: Session, model, object_id):
    instance = session.get(model, object_id)
    if instance is None:
        raise DomainError(404, "not_found", "Nie znaleziono zasobu.")
    return instance


def commit_and_refresh(session: Session, instance):
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


@router.post("/specialists", response_model=SpecialistRead, status_code=status.HTTP_201_CREATED)
def create_specialist(payload: SpecialistCreate, session: Session = Depends(get_session)):
    return commit_and_refresh(session, Specialist(**payload.model_dump()))


@router.get("/specialists", response_model=Page[SpecialistRead])
def list_specialists(
    search: str | None = None,
    active: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(Specialist)
    if search:
        statement = statement.where(Specialist.name.ilike(f"%{search}%"))
    if active is not None:
        statement = statement.where(Specialist.active == active)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    items = session.scalars(statement.order_by(Specialist.name).offset(offset).limit(limit)).all()
    return Page(items=list(items), total=total or 0, offset=offset, limit=limit)


@router.get("/specialists/{specialist_id}", response_model=SpecialistRead)
def get_specialist(specialist_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Specialist, specialist_id)


@router.patch("/specialists/{specialist_id}", response_model=SpecialistRead)
def update_specialist(
    specialist_id: uuid.UUID, payload: SpecialistUpdate, session: Session = Depends(get_session)
):
    specialist = get_or_404(session, Specialist, specialist_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(specialist, key, value)
    return commit_and_refresh(session, specialist)


@router.delete("/specialists/{specialist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_specialist(specialist_id: uuid.UUID, session: Session = Depends(get_session)):
    specialist = get_or_404(session, Specialist, specialist_id)
    session.delete(specialist)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, session: Session = Depends(get_session)):
    get_or_404(session, Specialist, payload.specialist_id)
    return commit_and_refresh(session, Service(**payload.model_dump()))


@router.get("/services", response_model=Page[ServiceRead])
def list_services(
    specialist_id: uuid.UUID | None = None,
    active: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(Service)
    if specialist_id:
        statement = statement.where(Service.specialist_id == specialist_id)
    if active is not None:
        statement = statement.where(Service.active == active)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    items = session.scalars(statement.order_by(Service.name).offset(offset).limit(limit)).all()
    return Page(items=list(items), total=total or 0, offset=offset, limit=limit)


@router.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, Service, service_id)


@router.patch("/services/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: uuid.UUID, payload: ServiceUpdate, session: Session = Depends(get_session)
):
    service = get_or_404(session, Service, service_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    return commit_and_refresh(session, service)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: uuid.UUID, session: Session = Depends(get_session)):
    service = get_or_404(session, Service, service_id)
    session.delete(service)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/availability-rules", response_model=AvailabilityRuleRead, status_code=201)
def create_availability_rule(
    payload: AvailabilityRuleCreate, session: Session = Depends(get_session)
):
    get_or_404(session, Specialist, payload.specialist_id)
    return commit_and_refresh(session, AvailabilityRule(**payload.model_dump()))


@router.get("/availability-rules", response_model=list[AvailabilityRuleRead])
def list_availability_rules(specialist_id: uuid.UUID, session: Session = Depends(get_session)):
    return list(
        session.scalars(
            select(AvailabilityRule)
            .where(AvailabilityRule.specialist_id == specialist_id)
            .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
        ).all()
    )


@router.get("/availability-rules/{rule_id}", response_model=AvailabilityRuleRead)
def get_availability_rule(rule_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, AvailabilityRule, rule_id)


@router.put("/availability-rules/{rule_id}", response_model=AvailabilityRuleRead)
def replace_availability_rule(
    rule_id: uuid.UUID,
    payload: AvailabilityRuleCreate,
    session: Session = Depends(get_session),
):
    get_or_404(session, Specialist, payload.specialist_id)
    rule = get_or_404(session, AvailabilityRule, rule_id)
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    return commit_and_refresh(session, rule)


@router.delete("/availability-rules/{rule_id}", status_code=204)
def delete_availability_rule(rule_id: uuid.UUID, session: Session = Depends(get_session)):
    rule = get_or_404(session, AvailabilityRule, rule_id)
    session.delete(rule)
    session.commit()
    return Response(status_code=204)


@router.post("/availability-exceptions", response_model=AvailabilityExceptionRead, status_code=201)
def create_availability_exception(
    payload: AvailabilityExceptionCreate, session: Session = Depends(get_session)
):
    get_or_404(session, Specialist, payload.specialist_id)
    return commit_and_refresh(session, AvailabilityException(**payload.model_dump()))


@router.get("/availability-exceptions", response_model=list[AvailabilityExceptionRead])
def list_availability_exceptions(specialist_id: uuid.UUID, session: Session = Depends(get_session)):
    return list(
        session.scalars(
            select(AvailabilityException)
            .where(AvailabilityException.specialist_id == specialist_id)
            .order_by(AvailabilityException.exception_date)
        ).all()
    )


@router.get("/availability-exceptions/{exception_id}", response_model=AvailabilityExceptionRead)
def get_availability_exception(exception_id: uuid.UUID, session: Session = Depends(get_session)):
    return get_or_404(session, AvailabilityException, exception_id)


@router.put("/availability-exceptions/{exception_id}", response_model=AvailabilityExceptionRead)
def replace_availability_exception(
    exception_id: uuid.UUID,
    payload: AvailabilityExceptionCreate,
    session: Session = Depends(get_session),
):
    get_or_404(session, Specialist, payload.specialist_id)
    exception = get_or_404(session, AvailabilityException, exception_id)
    for key, value in payload.model_dump().items():
        setattr(exception, key, value)
    return commit_and_refresh(session, exception)


@router.delete("/availability-exceptions/{exception_id}", status_code=204)
def delete_availability_exception(exception_id: uuid.UUID, session: Session = Depends(get_session)):
    exception = get_or_404(session, AvailabilityException, exception_id)
    session.delete(exception)
    session.commit()
    return Response(status_code=204)

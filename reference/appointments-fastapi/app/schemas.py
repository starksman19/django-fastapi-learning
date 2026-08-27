import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import AppointmentStatus


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


class SpecialistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    timezone: str = "UTC"
    active: bool = True

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Nieznana strefa czasowa IANA.") from exc
        return value


class SpecialistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    timezone: str | None = None
    active: bool | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Nieznana strefa czasowa IANA.") from exc
        return value


class SpecialistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    timezone: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ServiceCreate(BaseModel):
    specialist_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    duration_minutes: int = Field(gt=0, le=480)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    active: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    active: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    specialist_id: uuid.UUID
    name: str
    description: str
    duration_minutes: int
    price: Decimal
    active: bool
    created_at: datetime


class AvailabilityRuleCreate(BaseModel):
    specialist_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    starts_on: date | None = None
    ends_on: date | None = None
    active: bool = True

    @model_validator(mode="after")
    def validate_window(self):
        if self.start_time >= self.end_time:
            raise ValueError("Początek dostępności musi poprzedzać koniec.")
        if self.starts_on and self.ends_on and self.starts_on > self.ends_on:
            raise ValueError("starts_on nie może być późniejsze niż ends_on.")
        return self


class AvailabilityRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    specialist_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    starts_on: date | None
    ends_on: date | None
    active: bool


class AvailabilityExceptionCreate(BaseModel):
    specialist_id: uuid.UUID
    exception_date: date
    available: bool = False
    start_time: time | None = None
    end_time: time | None = None
    reason: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def validate_window(self):
        if self.available:
            if self.start_time is None or self.end_time is None or self.start_time >= self.end_time:
                raise ValueError("Dostępny wyjątek wymaga poprawnego przedziału czasu.")
        elif self.start_time is not None or self.end_time is not None:
            raise ValueError("Niedostępny dzień nie przyjmuje przedziału czasu.")
        return self


class AvailabilityExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    specialist_id: uuid.UUID
    exception_date: date
    available: bool
    start_time: time | None
    end_time: time | None
    reason: str


class AppointmentCreate(BaseModel):
    specialist_id: uuid.UUID
    service_id: uuid.UUID
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: EmailStr
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def starts_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at musi zawierać przesunięcie strefy czasowej.")
        return value


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    specialist_id: uuid.UUID
    service_id: uuid.UUID
    customer_name: str
    customer_email: EmailStr
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime


class SlotRead(BaseModel):
    starts_at: datetime
    ends_at: datetime

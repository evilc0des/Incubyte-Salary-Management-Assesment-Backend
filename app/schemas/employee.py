from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    job_title: str
    department: str | None = None
    country: str
    salary: Decimal = Field(gt=0)
    hire_date: date | None = None

    model_config = ConfigDict(extra="forbid")


class EmployeeReplace(EmployeeCreate):
    pass


class EmployeePatch(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    country: str | None = None
    salary: Decimal | None = Field(default=None, gt=0)
    hire_date: date | None = None

    model_config = ConfigDict(extra="forbid")


class EmployeeRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    job_title: str
    department: str | None
    country: str
    salary: Decimal
    currency: str
    hire_date: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeRead]
    total: int
    limit: int
    offset: int
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


class EmployeeInsightsFilters(BaseModel):
    country: str | None
    job_title: str | None


class EmployeeInsightsMetrics(BaseModel):
    employee_count: int
    currency: str
    min_salary: Decimal | None
    max_salary: Decimal | None
    average_salary: Decimal | None
    median_salary: Decimal | None
    p25_salary: Decimal | None
    p75_salary: Decimal | None
    salary_range: Decimal | None
    last_updated_at: datetime | None


class EmployeeInsightsOverview(EmployeeInsightsMetrics):
    filters: EmployeeInsightsFilters


class CountryInsightsRow(EmployeeInsightsMetrics):
    country: str


class CountryInsightsListResponse(BaseModel):
    items: list[CountryInsightsRow]
    total: int
    limit: int
    offset: int


class DepartmentInsightsRow(EmployeeInsightsMetrics):
    department: str


class DepartmentInsightsListResponse(BaseModel):
    items: list[DepartmentInsightsRow]
    total: int
    limit: int
    offset: int


class TenureBandInsightsRow(EmployeeInsightsMetrics):
    tenure_band: str


class TenureBandInsightsListResponse(BaseModel):
    items: list[TenureBandInsightsRow]
    total: int


class JobTitleInsightsRow(EmployeeInsightsMetrics):
    job_title: str


class JobTitleInsightsListResponse(BaseModel):
    items: list[JobTitleInsightsRow]
    total: int
    limit: int
    offset: int


class HiringTrendRow(BaseModel):
    month: str
    hires_count: int


class HiringTrendResponse(BaseModel):
    items: list[HiringTrendRow]
    total: int
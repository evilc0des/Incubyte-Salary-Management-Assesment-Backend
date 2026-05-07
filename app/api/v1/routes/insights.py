from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from typing import Callable

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    CountryInsightsListResponse,
    CountryInsightsRow,
    DepartmentInsightsListResponse,
    DepartmentInsightsRow,
    EmployeeInsightsFilters,
    EmployeeInsightsMetrics,
    EmployeeInsightsOverview,
    HiringTrendResponse,
    HiringTrendRow,
    JobTitleInsightsListResponse,
    JobTitleInsightsRow,
    TenureBandInsightsListResponse,
    TenureBandInsightsRow,
)

router = APIRouter(prefix="/insights", tags=["insights"])

SALARY_QUANTUM = Decimal("0.01")
TENURE_BANDS: tuple[tuple[str, int | None, int | None], ...] = (
    ("<1 year", None, 1),
    ("1-2 years", 1, 3),
    ("3-5 years", 3, 6),
    ("5+ years", 6, None),
)


def _quantize_salary(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(SALARY_QUANTUM)


def _calculate_percentile(sorted_salaries: list[Decimal], percentile: Decimal) -> Decimal | None:
    if not sorted_salaries:
        return None

    position = percentile * Decimal(len(sorted_salaries) - 1)
    lower_index = int(position.to_integral_value(rounding=ROUND_FLOOR))
    upper_index = min(lower_index + 1, len(sorted_salaries) - 1)
    fraction = position - Decimal(lower_index)
    lower_value = sorted_salaries[lower_index]
    upper_value = sorted_salaries[upper_index]

    return _quantize_salary(lower_value + (upper_value - lower_value) * fraction)


def _calculate_metrics(employees: list[Employee]) -> EmployeeInsightsMetrics:
    if not employees:
        return EmployeeInsightsMetrics(
            employee_count=0,
            currency="USD",
            min_salary=None,
            max_salary=None,
            average_salary=None,
            median_salary=None,
            p25_salary=None,
            p75_salary=None,
            salary_range=None,
            last_updated_at=None,
        )

    salaries = sorted(employee.salary for employee in employees)
    minimum_salary = _quantize_salary(salaries[0])
    maximum_salary = _quantize_salary(salaries[-1])
    average_salary = _quantize_salary(sum(salaries) / Decimal(len(salaries)))
    last_updated_at = max(employee.updated_at for employee in employees)

    return EmployeeInsightsMetrics(
        employee_count=len(employees),
        currency="USD",
        min_salary=minimum_salary,
        max_salary=maximum_salary,
        average_salary=average_salary,
        median_salary=_calculate_percentile(salaries, Decimal("0.50")),
        p25_salary=_calculate_percentile(salaries, Decimal("0.25")),
        p75_salary=_calculate_percentile(salaries, Decimal("0.75")),
        salary_range=_quantize_salary(maximum_salary - minimum_salary),
        last_updated_at=last_updated_at,
    )


def _load_employees_for_insights(
    db: Session,
    *,
    country: str | None = None,
    job_title: str | None = None,
) -> list[Employee]:
    statement = select(Employee)

    if country is not None:
        statement = statement.where(Employee.country == country)
    if job_title is not None:
        statement = statement.where(Employee.job_title == job_title)

    return db.scalars(statement.order_by(Employee.country, Employee.job_title, Employee.salary, Employee.id)).all()


def _group_employees_by_label(
    employees: list[Employee],
    label_getter: Callable[[Employee], str | None],
    *,
    fallback_label: str,
) -> dict[str, list[Employee]]:
    grouped_employees: dict[str, list[Employee]] = defaultdict(list)

    for employee in employees:
        grouped_employees[label_getter(employee) or fallback_label].append(employee)

    return grouped_employees


def _full_years_between(start_date: date, end_date: date) -> int:
    years = end_date.year - start_date.year
    if (end_date.month, end_date.day) < (start_date.month, start_date.day):
        years -= 1
    return max(years, 0)


def _get_tenure_band_label(hire_date: date, reference_date: date) -> str:
    full_years = _full_years_between(hire_date, reference_date)

    for label, minimum_years, maximum_years in TENURE_BANDS:
        if minimum_years is not None and full_years < minimum_years:
            continue
        if maximum_years is not None and full_years >= maximum_years:
            continue
        return label

    return TENURE_BANDS[-1][0]


def _start_of_month(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, months: int) -> date:
    absolute_month = (value.year * 12 + value.month - 1) + months
    year = absolute_month // 12
    month = absolute_month % 12 + 1
    return date(year, month, 1)


def _build_tenure_band_items(employees: list[Employee], *, reference_date: date) -> list[TenureBandInsightsRow]:
    employees_by_band: dict[str, list[Employee]] = {label: [] for label, _, _ in TENURE_BANDS}

    for employee in employees:
        employees_by_band[_get_tenure_band_label(employee.hire_date, reference_date)].append(employee)

    return [
        TenureBandInsightsRow(tenure_band=label, **_calculate_metrics(employees_by_band[label]).model_dump())
        for label, _, _ in TENURE_BANDS
    ]


def _build_hiring_trend_items(
    employees: list[Employee],
    *,
    months: int,
    reference_date: date,
) -> list[HiringTrendRow]:
    current_month = _start_of_month(reference_date)
    month_starts = [_shift_month(current_month, offset) for offset in range(-(months - 1), 1)]
    hires_by_month = {month_start: 0 for month_start in month_starts}

    for employee in employees:
        hire_month = _start_of_month(employee.hire_date)
        if hire_month in hires_by_month:
            hires_by_month[hire_month] += 1

    return [
        HiringTrendRow(month=month_start.strftime("%Y-%m"), hires_count=hires_by_month[month_start])
        for month_start in month_starts
    ]


def _paginate_items[T](items: list[T], limit: int, offset: int) -> tuple[list[T], int]:
    return items[offset : offset + limit], len(items)


def _sort_grouped_metrics_by_average[T](
    items: list[T],
    value_getter: Callable[[T], Decimal | None],
    label_getter: Callable[[T], str],
) -> list[T]:
    return sorted(
        items,
        key=lambda item: (-(value_getter(item) or Decimal("0.00")), label_getter(item)),
    )


def _sort_grouped_metrics_by_count[T](
    items: list[T],
    count_getter: Callable[[T], int],
    label_getter: Callable[[T], str],
) -> list[T]:
    return sorted(
        items,
        key=lambda item: (-count_getter(item), label_getter(item)),
    )


@router.get(
    "/overview",
    summary="Get employee salary insights overview",
    response_model=EmployeeInsightsOverview,
)
def get_employee_insights_overview(
    country: str | None = Query(default=None, min_length=1),
    job_title: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> EmployeeInsightsOverview:
    employees = _load_employees_for_insights(db, country=country, job_title=job_title)
    metrics = _calculate_metrics(employees)

    return EmployeeInsightsOverview(
        filters=EmployeeInsightsFilters(country=country, job_title=job_title),
        **metrics.model_dump(),
    )


@router.get(
    "/by-country",
    summary="List employee salary insights by country",
    response_model=CountryInsightsListResponse,
)
def list_employee_insights_by_country(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CountryInsightsListResponse:
    employees = _load_employees_for_insights(db)
    employees_by_country = _group_employees_by_label(
        employees,
        label_getter=lambda employee: employee.country,
        fallback_label="Unknown",
    )

    items = [
        CountryInsightsRow(country=country, **_calculate_metrics(group).model_dump())
        for country, group in employees_by_country.items()
    ]
    items = _sort_grouped_metrics_by_average(
        items,
        value_getter=lambda item: item.average_salary,
        label_getter=lambda item: item.country,
    )
    paginated_items, total = _paginate_items(items, limit, offset)

    return CountryInsightsListResponse(items=paginated_items, total=total, limit=limit, offset=offset)


@router.get(
    "/by-department",
    summary="List employee salary insights by department",
    response_model=DepartmentInsightsListResponse,
)
def list_employee_insights_by_department(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DepartmentInsightsListResponse:
    employees = _load_employees_for_insights(db)
    employees_by_department = _group_employees_by_label(
        employees,
        label_getter=lambda employee: employee.department,
        fallback_label="Unassigned",
    )

    items = [
        DepartmentInsightsRow(department=department, **_calculate_metrics(group).model_dump())
        for department, group in employees_by_department.items()
    ]
    items = _sort_grouped_metrics_by_count(
        items,
        count_getter=lambda item: item.employee_count,
        label_getter=lambda item: item.department,
    )
    paginated_items, total = _paginate_items(items, limit, offset)

    return DepartmentInsightsListResponse(items=paginated_items, total=total, limit=limit, offset=offset)


@router.get(
    "/tenure-bands",
    summary="List employee insights by tenure band",
    response_model=TenureBandInsightsListResponse,
)
def list_employee_insights_by_tenure_band(
    db: Session = Depends(get_db),
) -> TenureBandInsightsListResponse:
    employees = _load_employees_for_insights(db)
    items = _build_tenure_band_items(employees, reference_date=date.today())
    return TenureBandInsightsListResponse(items=items, total=len(items))


@router.get(
    "/hiring-trend",
    summary="List employee hiring trend by month",
    response_model=HiringTrendResponse,
)
def get_employee_hiring_trend(
    months: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
) -> HiringTrendResponse:
    employees = _load_employees_for_insights(db)
    items = _build_hiring_trend_items(employees, months=months, reference_date=date.today())
    return HiringTrendResponse(items=items, total=len(items))


@router.get(
    "/by-country/{country}/job-titles",
    summary="List employee salary insights by job title in a country",
    response_model=JobTitleInsightsListResponse,
)
def list_employee_insights_by_job_title(
    country: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> JobTitleInsightsListResponse:
    employees = _load_employees_for_insights(db, country=country)
    employees_by_job_title = _group_employees_by_label(
        employees,
        label_getter=lambda employee: employee.job_title,
        fallback_label="Unknown",
    )

    items = [
        JobTitleInsightsRow(job_title=job_title, **_calculate_metrics(group).model_dump())
        for job_title, group in employees_by_job_title.items()
    ]
    items = _sort_grouped_metrics_by_average(
        items,
        value_getter=lambda item: item.average_salary,
        label_getter=lambda item: item.job_title,
    )
    paginated_items, total = _paginate_items(items, limit, offset)

    return JobTitleInsightsListResponse(items=paginated_items, total=total, limit=limit, offset=offset)
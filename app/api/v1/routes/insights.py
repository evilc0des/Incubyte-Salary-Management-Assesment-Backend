from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    CountryInsightsListResponse,
    CountryInsightsRow,
    EmployeeInsightsFilters,
    EmployeeInsightsMetrics,
    EmployeeInsightsOverview,
    JobTitleInsightsListResponse,
    JobTitleInsightsRow,
)

router = APIRouter(prefix="/insights", tags=["insights"])

SALARY_QUANTUM = Decimal("0.01")


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


def _paginate_items[T](items: list[T], limit: int, offset: int) -> tuple[list[T], int]:
    return items[offset : offset + limit], len(items)


def _sort_grouped_metrics_by_average[T](items: list[T], value_getter: callable, label_getter: callable) -> list[T]:
    return sorted(
        items,
        key=lambda item: (-(value_getter(item) or Decimal("0.00")), label_getter(item)),
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
    employees_by_country: dict[str, list[Employee]] = defaultdict(list)

    for employee in employees:
        employees_by_country[employee.country].append(employee)

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
    employees_by_job_title: dict[str, list[Employee]] = defaultdict(list)

    for employee in employees:
        employees_by_job_title[employee.job_title].append(employee)

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
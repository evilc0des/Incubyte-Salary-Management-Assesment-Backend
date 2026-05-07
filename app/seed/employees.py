from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import islice
from pathlib import Path
from random import Random
from time import perf_counter

from sqlalchemy import insert
from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Employee


DEFAULT_EMPLOYEE_COUNT = 10_000
DEFAULT_BATCH_SIZE = 2_000
DEFAULT_RANDOM_SEED = 20_260_506
NAME_MAX_LENGTH = 50

JOB_TITLES: tuple[str, ...] = (
    "Software Engineer",
    "Senior Software Engineer",
    "Engineering Manager",
    "Product Manager",
    "Data Analyst",
    "QA Engineer",
    "HR Business Partner",
    "Finance Analyst",
    "Sales Manager",
    "Support Specialist",
)

DEPARTMENTS: tuple[str | None, ...] = (
    "Engineering",
    "Product",
    "Data",
    "Quality",
    "Human Resources",
    "Finance",
    "Sales",
    "Customer Success",
    None,
)

COUNTRIES: tuple[str, ...] = (
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "India",
    "Australia",
    "Singapore",
    "United Arab Emirates",
)


@dataclass(frozen=True)
class SeedEmployeesResult:
    inserted_count: int
    batch_count: int
    duration_seconds: float


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed the employees table with generated records.")
    parser.add_argument("--first-names-path", required=True, type=Path)
    parser.add_argument("--last-names-path", required=True, type=Path)
    parser.add_argument("--count", type=int, default=DEFAULT_EMPLOYEE_COUNT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    return parser


def _load_names(path: Path, *, label: str) -> list[str]:
    if not path.exists():
        raise ValueError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} path is not a file: {path}")

    names: list[str] = []
    invalid_names: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            candidate = raw_line.strip()
            if not candidate:
                continue
            if len(candidate) > NAME_MAX_LENGTH:
                invalid_names.append(candidate)
                continue
            names.append(candidate)

    if invalid_names:
        raise ValueError(
            f"{label} file contains {len(invalid_names)} value(s) longer than {NAME_MAX_LENGTH} characters"
        )
    if not names:
        raise ValueError(f"{label} file did not contain any usable names: {path}")
    return names


def _validate_positive_int(value: int, *, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _build_salary(randomizer: Random, *, row_number: int) -> Decimal:
    base_salary = 55_000 + ((row_number * 1_379) % 110_000)
    salary_offset = randomizer.randint(0, 9_999)
    return Decimal(base_salary + salary_offset).quantize(Decimal("0.01"))


def _build_hire_date(randomizer: Random, *, row_number: int) -> date:
    days_back = randomizer.randint(0, 365 * 8) + (row_number % 90)
    return date.today() - timedelta(days=days_back)


def _generate_employee_rows(
    *,
    first_names: list[str],
    last_names: list[str],
    count: int,
    seed: int,
):
    randomizer = Random(seed)
    for row_number in range(count):
        yield {
            "first_name": randomizer.choice(first_names),
            "last_name": randomizer.choice(last_names),
            "job_title": JOB_TITLES[row_number % len(JOB_TITLES)],
            "department": DEPARTMENTS[row_number % len(DEPARTMENTS)],
            "country": COUNTRIES[(row_number + seed) % len(COUNTRIES)],
            "salary": _build_salary(randomizer, row_number=row_number),
            "hire_date": _build_hire_date(randomizer, row_number=row_number),
        }


def _batched_rows(rows, batch_size: int):
    iterator = iter(rows)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def seed_employees(
    session_factory: sessionmaker[Session],
    *,
    first_names_path: Path,
    last_names_path: Path,
    count: int = DEFAULT_EMPLOYEE_COUNT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    seed: int = DEFAULT_RANDOM_SEED,
) -> SeedEmployeesResult:
    _validate_positive_int(count, label="count")
    _validate_positive_int(batch_size, label="batch_size")

    first_names = _load_names(first_names_path, label="first_names")
    last_names = _load_names(last_names_path, label="last_names")

    started_at = perf_counter()
    batch_count = 0

    with session_factory() as session:
        for batch in _batched_rows(
            _generate_employee_rows(
                first_names=first_names,
                last_names=last_names,
                count=count,
                seed=seed,
            ),
            batch_size,
        ):
            session.execute(insert(Employee), batch)
            session.commit()
            batch_count += 1

    return SeedEmployeesResult(
        inserted_count=count,
        batch_count=batch_count,
        duration_seconds=perf_counter() - started_at,
    )


def main(argv: list[str] | None = None, *, session_factory: sessionmaker[Session]) -> int:
    args = _build_argument_parser().parse_args(argv)
    result = seed_employees(
        session_factory,
        first_names_path=args.first_names_path,
        last_names_path=args.last_names_path,
        count=args.count,
        batch_size=args.batch_size,
        seed=args.seed,
    )
    print(
        f"Seeded {result.inserted_count} employees in {result.batch_count} batch(es) "
        f"over {result.duration_seconds:.2f}s"
    )
    return 0
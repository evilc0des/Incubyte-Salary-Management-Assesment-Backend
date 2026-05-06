from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import CheckConstraint, Computed, Date, DateTime, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("salary > 0", name="check_positive_salary"),
        CheckConstraint("length(currency) = 3", name="check_currency_format"),
        CheckConstraint(
            "length(first_name) > 0 AND length(last_name) > 0",
            name="check_names_not_empty",
        ),
        Index("idx_salary_insights_composite", "country", "job_title", "salary"),
        Index("idx_employees_country", "country"),
        Index("idx_employees_job_title", "job_title"),
        Index(
            "idx_employees_full_name_search",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str] = mapped_column(
        String(101),
        Computed("first_name || ' ' || last_name", persisted=True),
    )
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'USD'"),
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
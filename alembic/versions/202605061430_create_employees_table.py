from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202605061430"
down_revision = "202605061325"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "employees",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column(
            "full_name",
            sa.String(length=101),
            sa.Computed("first_name || ' ' || last_name", persisted=True),
            nullable=False,
        ),
        sa.Column("job_title", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("salary", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("hire_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("salary > 0", name="check_positive_salary"),
        sa.CheckConstraint("length(currency) = 3", name="check_currency_format"),
        sa.CheckConstraint(
            "length(first_name) > 0 AND length(last_name) > 0",
            name="check_names_not_empty",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_salary_insights_composite",
        "employees",
        ["country", "job_title", "salary"],
        unique=False,
    )
    op.create_index("idx_employees_country", "employees", ["country"], unique=False)
    op.create_index("idx_employees_job_title", "employees", ["job_title"], unique=False)
    op.create_index(
        "idx_employees_full_name_search",
        "employees",
        ["full_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
        """
    )
    op.execute(
        """
        CREATE TRIGGER update_employees_modtime
            BEFORE UPDATE ON employees
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_employees_modtime ON employees")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    op.drop_index("idx_employees_full_name_search", table_name="employees")
    op.drop_index("idx_employees_job_title", table_name="employees")
    op.drop_index("idx_employees_country", table_name="employees")
    op.drop_index("idx_salary_insights_composite", table_name="employees")
    op.drop_table("employees")
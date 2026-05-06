import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeePatch,
    EmployeeRead,
    EmployeeReplace,
)

router = APIRouter(prefix="/employees", tags=["employees"])


def _get_employee_or_404(employee_id: uuid.UUID, db: Session) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.get("", summary="List employees", response_model=EmployeeListResponse)
def list_employees(
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EmployeeListResponse:
    statement = select(Employee)
    count_statement = select(func.count()).select_from(Employee)

    if search:
        search_term = f"%{search}%"
        statement = statement.where(Employee.full_name.ilike(search_term))
        count_statement = count_statement.where(Employee.full_name.ilike(search_term))

    employees = db.scalars(
        statement.order_by(Employee.full_name, Employee.id).limit(limit).offset(offset)
    ).all()
    total = db.scalar(count_statement) or 0

    return EmployeeListResponse(items=employees, total=total, limit=limit, offset=offset)


@router.post("", summary="Create employee", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(employee_in: EmployeeCreate, db: Session = Depends(get_db)) -> Employee:
    employee = Employee(**employee_in.model_dump(exclude_unset=True))
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/{employee_id}", summary="Get employee", response_model=EmployeeRead)
def get_employee(employee_id: uuid.UUID, db: Session = Depends(get_db)) -> Employee:
    return _get_employee_or_404(employee_id, db)


@router.put("/{employee_id}", summary="Replace employee", response_model=EmployeeRead)
def replace_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeeReplace,
    db: Session = Depends(get_db),
) -> Employee:
    employee = _get_employee_or_404(employee_id, db)

    for field_name, value in employee_in.model_dump().items():
        setattr(employee, field_name, value)

    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", summary="Update employee", response_model=EmployeeRead)
def update_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeePatch,
    db: Session = Depends(get_db),
) -> Employee:
    employee = _get_employee_or_404(employee_id, db)

    for field_name, value in employee_in.model_dump(exclude_unset=True).items():
        setattr(employee, field_name, value)

    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", summary="Delete employee", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    employee = _get_employee_or_404(employee_id, db)
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
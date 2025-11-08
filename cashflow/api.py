# budget_api.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, validator
from cashflow.data import ( upsert_recurring_item, upsert_single_item, delete_recurring_item, delete_single_item, update_current_values, fetch_account_movements )

router = APIRouter()


# ---------- Models ----------

class IntervalUnit(str, Enum):
    days = "day"
    weeks = "week"
    months = "month"
    years = "year"


class UpsertSingleItemRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    date: date
    category: str
    description: str
    type: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this item is active.")

    @validator("amount")
    def quantize_amount(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))


class UpsertRecurringItemRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    every: int = Field(..., gt=0, description="Repetition interval count.")
    unit: IntervalUnit = Field(..., description="Unit for the 'every' field.")
    category: str
    description: str
    dateFrom: date
    dateTo: Optional[date] = None
    type: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this recurring item is active.")

    @validator("amount")
    def quantize_amount(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))

    @validator("dateTo")
    def validate_date_range(cls, v: Optional[date], values) -> Optional[date]:
        if v and "dateFrom" in values and v < values["dateFrom"]:
            raise ValueError("date_to cannot be before dateFrom")
        return v


class EditCurrentValuesRequest(BaseModel):
    bank_account_amount: Decimal = Field(..., description="Current bank account balance.")
    cash_amount: Decimal = Field(..., description="Current cash balance.")
    range_start: date
    range_end: date

    @validator("bank_account_amount", "cash_amount")
    def quantize_money(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))

    @validator("range_end")
    def validate_range(cls, v: date, values) -> date:
        if "range_start" in values and v < values["range_start"]:
            raise ValueError("range_end cannot be before range_start")
        return v


@router.post("/recurring", status_code=status.HTTP_202_ACCEPTED, summary="Upsert recurring item")
def upsert_recurring_item_api(payload: UpsertRecurringItemRequest):
    effective_id = payload.id or uuid4()
    upsert_recurring_item(
        id=effective_id,
        every=payload.every,
        unit=payload.unit.value,
        category=payload.category,
        description=payload.description,
        date_from=payload.dateFrom,
        date_to=payload.dateTo,
        type_=payload.type,
        amount=payload.amount,
        enabled=payload.enabled,
    )
    return {"status": "ok", "id": str(effective_id)}


@router.post("/single", status_code=status.HTTP_202_ACCEPTED, summary="Upsert single item")
def upsert_single_item_api(payload: UpsertSingleItemRequest):
    effective_id = payload.id or uuid4()
    upsert_single_item(
        id=effective_id,
        date_=payload.date,
        category=payload.category,
        description=payload.description,
        type_= payload.type,
        amount=payload.amount,
        enabled=payload.enabled,
    )
    return {"status": "ok", "id": str(effective_id)}


@router.delete("/recurring/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete recurring item")
def delete_recurring_item_api(item_id: UUID):
    deleted = delete_recurring_item(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}


@router.delete("/single/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete single item")
def delete_single_item_api(item_id: UUID):
    deleted = delete_single_item(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}


@router.put("/current-values", status_code=status.HTTP_202_ACCEPTED, summary="Edit current values")
def edit_current_values_api(payload: EditCurrentValuesRequest):
    update_current_values(
        bank_account_amount=payload.bank_account_amount,
        cash_amount=payload.cash_amount,
        range_start=payload.range_start,
        range_end=payload.range_end,
    )
    return {"status": "ok"}

@router.get("/account-movements")
def get_account_movements():
    return fetch_account_movements()
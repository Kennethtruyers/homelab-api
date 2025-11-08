# budget_api.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Query, Response, status
from pydantic import BaseModel, Field, validator
from cashflow.data import ( 
    fetch_accounts, upsert_account,
    upsert_recurring_item, fetch_recurring_items, delete_recurring_item, 
    upsert_single_item, fetch_single_items, delete_single_item, 
    update_current_values, fetch_current_values, 
    fetch_account_movements )

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
    accountId: UUID

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
    accountId: UUID

    @validator("amount")
    def quantize_amount(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))

    @validator("dateTo")
    def validate_date_range(cls, v: Optional[date], values) -> Optional[date]:
        if v and "dateFrom" in values and v < values["dateFrom"]:
            raise ValueError("date_to cannot be before dateFrom")
        return v


class EditCurrentValuesRequest(BaseModel):
    bank: Decimal = Field(..., description="Current bank account balance.")
    cash: Decimal = Field(..., description="Current cash balance.")
    start: date
    end: date

    @validator("bank", "cash")
    def quantize_money(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))

    @validator("end")
    def validate_range(cls, v: date, values) -> date:
        if "start" in values and v < values["start"]:
            raise ValueError("end cannot be before start")
        return v

class EditAccountRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    amount: Decimal = Field(..., description="Current cash balance.")
    name: str
    date: date


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
        account_id = payload.accountId
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
        account_id = payload.accountId
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
        bank_account_amount=payload.bank,
        cash_amount=payload.cash,
        range_start=payload.start,
        range_end=payload.end,
    )
    return {"status": "ok"}

@router.get("/account-movements")
def get_account_movements(accountId: Optional[str] = Query(None), until: Optional[date] = Query(None)):
    return fetch_account_movements(accountId, until)

@router.get("/single")
def get_single_items(accountId: Optional[str] = Query(None)):
    return fetch_single_items(accountId)

@router.get("/recurring")
def get_recurring_items(accountId: Optional[str] = Query(None)):
    return fetch_recurring_items(accountId)

@router.get("/current-values")
def get_current_values():
    return fetch_current_values()

@router.get("/accounts")
def get_accounts():
    return fetch_accounts()

@router.put("/accounts", status_code=status.HTTP_202_ACCEPTED, summary="Upsert account")
def upsert_acount_api(payload: EditAccountRequest):
    upsert_account(
        id=payload.id,
        amount=payload.amount,
        name=payload.name,
        date=payload.date,
    )
    return {"status": "ok"}
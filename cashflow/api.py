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
    upsert_recurring_item, fetch_recurring_items, delete_recurring_item, upsert_recurring_item_override, fetch_recurring_items_overrides, delete_recurring_item_override,
    upsert_single_item, fetch_single_items, delete_single_item,  upsert_single_item_override, fetch_single_items_overrides, delete_single_item_override,
    upsert_scenario, fetch_scenarios,
    fetch_account_movements )

router = APIRouter()


# ---------- Models ----------
class IntervalUnit(str, Enum):
    days = "day"
    weeks = "week"
    months = "month"
    years = "year"

class OpUnit(str, Enum):
    add = "add"
    replace = "replace"

class UpsertSingleItemRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    date: date
    category: str
    description: str
    kind: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this item is active.")
    accountId: UUID

class UpsertSingleOverrideRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    date: date
    category: str
    description: str
    kind: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this item is active.")
    accountId: UUID
    scenarioId: UUID
    targetSingleId: UUID
    op: OpUnit

class UpsertRecurringItemRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    every: int = Field(..., gt=0, description="Repetition interval count.")
    unit: IntervalUnit = Field(..., description="Unit for the 'every' field.")
    category: str
    description: str
    dateFrom: date
    dateTo: Optional[date] = None
    kind: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this recurring item is active.")
    accountId: UUID

    @validator("dateTo")
    def validate_date_range(cls, v: Optional[date], values) -> Optional[date]:
        if v and "dateFrom" in values and v < values["dateFrom"]:
            raise ValueError("date_to cannot be before dateFrom")
        return v

class UpsertRecurringOverrideRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    every: int = Field(..., gt=0, description="Repetition interval count.")
    unit: IntervalUnit = Field(..., description="Unit for the 'every' field.")
    category: str
    description: str
    dateFrom: date
    dateTo: Optional[date] = None
    kind: str
    amount: Decimal = Field(..., description="Negative for expenses, positive for income.")
    enabled: bool = Field(True, description="Whether this recurring item is active.")
    accountId: UUID
    scenarioId: UUID
    targetRecurringId: UUID
    op: OpUnit

    @validator("dateTo")
    def validate_date_range(cls, v: Optional[date], values) -> Optional[date]:
        if v and "dateFrom" in values and v < values["dateFrom"]:
            raise ValueError("date_to cannot be before dateFrom")
        return v

class EditAccountRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    amount: Decimal = Field(..., description="Current cash balance.")
    name: str
    date: date
    enddate: date
    type: str
    liquid: bool

class EditScenarioRequest(BaseModel):
    id: Optional[UUID] = Field(None, description="Present to update, absent to create.")
    name: str
    description: str

#--- Recurring items ---

@router.get("/recurring")
def get_recurring_items(accountId: Optional[str] = Query(None)):
    return fetch_recurring_items(accountId)

@router.post("/recurring", status_code=status.HTTP_202_ACCEPTED, summary="Upsert recurring item")
def upsert_recurring_item_api(payload: UpsertRecurringItemRequest):
    effective_id = payload.id or uuid4()
    upsert_recurring_item(
        id=effective_id,
        every=payload.every,
        unit=payload.unit.value,
        category=payload.category,
        description=payload.description,
        dateFrom=payload.dateFrom,
        dateTo=payload.dateTo,
        kind=payload.kind,
        amount=payload.amount,
        enabled=payload.enabled,
        account_id = payload.accountId
    )
    return {"status": "ok", "id": str(effective_id)}

@router.delete("/recurring/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete recurring item")
def delete_recurring_item_api(item_id: UUID):
    deleted = delete_recurring_item(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}

# --- Recurring overrides

@router.get("/recurring-override")
def get_recurring_overrides(accountId: Optional[str] = Query(None), scenarioId: Optional[str] = Query(None)):
    return fetch_recurring_items_overrides(accountId, scenarioId)

@router.post("/recurring-override", status_code=status.HTTP_202_ACCEPTED, summary="Upsert recurring override")
def upsert_recurring_override_api(payload: UpsertRecurringOverrideRequest):
    effective_id = payload.id or uuid4()
    upsert_recurring_item_override(
        id=effective_id,
        every=payload.every,
        unit=payload.unit.value,
        category=payload.category,
        description=payload.description,
        dateFrom=payload.dateFrom,
        dateTo=payload.dateTo,
        kind=payload.kind,
        amount=payload.amount,
        enabled=payload.enabled,
        account_id = payload.accountId,
        targetRecurringId = payload.targetRecurringId,
        op = payload.op.value,
        scenarioId = payload.scenarioId
    )
    return {"status": "ok", "id": str(effective_id)}

@router.delete("/recurring-override/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete recurring item")
def delete_recurring_item_override_api(item_id: UUID):
    deleted = delete_recurring_item_override(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}

#--- Single Items ---

@router.get("/single")
def get_single_items(accountId: Optional[str] = Query(None)):
    return fetch_single_items(accountId)

@router.post("/single", status_code=status.HTTP_202_ACCEPTED, summary="Upsert single item")
def upsert_single_item_api(payload: UpsertSingleItemRequest):
    effective_id = payload.id or uuid4()
    upsert_single_item(
        id=effective_id,
        date_=payload.date,
        category=payload.category,
        description=payload.description,
        kind= payload.kind,
        amount=payload.amount,
        enabled=payload.enabled,
        account_id = payload.accountId
    )
    return {"status": "ok", "id": str(effective_id)}

@router.delete("/single/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete single item")
def delete_single_item_api(item_id: UUID):
    deleted = delete_single_item(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}
# --- Single overrides

@router.get("/single-override")
def get_single_overrides(accountId: Optional[str] = Query(None), scenarioId: Optional[str] = Query(None)):
    return fetch_single_items_overrides(accountId, scenarioId)

@router.post("/single-override", status_code=status.HTTP_202_ACCEPTED, summary="Upsert single override")
def upsert_single_override_api(payload: UpsertSingleOverrideRequest):
    effective_id = payload.id or uuid4()
    upsert_single_item_override(
        id=effective_id,
        date_=payload.date,
        category=payload.category,
        description=payload.description,
        kind= payload.kind,
        amount=payload.amount,
        enabled=payload.enabled,
        account_id = payload.accountId,
        targetSingleId = payload.targetSingleId,
        op = payload.op.value,
        scenarioId = payload.scenarioId
    )
    return {"status": "ok", "id": str(effective_id)}

@router.delete("/single-override/{item_id}", status_code=status.HTTP_202_ACCEPTED, summary="Delete single item")
def delete_single_item_override_api(item_id: UUID):
    deleted = delete_single_item_override(id=item_id)
    return {"status": "deleted" if deleted else "not_found", "id": str(item_id)}

# --- Account movements

@router.get("/account-movements")
def get_account_movements(accountId: str = Query(...), until: Optional[date] = Query(None)):
    return fetch_account_movements(accountId, until)

# --- Accounts

@router.get("/accounts")
def get_accounts():
    return fetch_accounts()

@router.put("/accounts", status_code=status.HTTP_202_ACCEPTED, summary="Upsert account")
def upsert_acount_api(payload: EditAccountRequest):
    effective_id = payload.id or uuid4()
    upsert_account(
        id=effective_id,
        amount=payload.amount,
        name=payload.name,
        date=payload.date,
        endDate=payload.enddate,
        type=payload.type,
        liquid=payload.liquid
    )
    return {"status": "ok", "id": str(effective_id)}

# --- Scenarios
@router.get("/scenarios")
def get_scenarios():
    return fetch_scenarios()

@router.put("/scenarios", status_code=status.HTTP_202_ACCEPTED, summary="Upsert scenario")
def upsert_scenario_api(payload: EditScenarioRequest):
    effective_id = payload.id or uuid4()
    upsert_scenario(
        id=effective_id,
        description=payload.description,
        name=payload.name
    )
    return {"status": "ok", "id": str(effective_id)}
from connections import get_cashflow_connection
from __future__ import annotations
from uuid import UUID
import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple
from psycopg import sql


def init():
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS single_items (
                    id UUID PRIMARY KEY,
                    "date" DATE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    enabled BOOLEAN NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS recurring_items (
                    id UUID PRIMARY KEY,
                    every INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    date_from DATE NOT NULL,
                    date_to DATE NULL,
                    "type" TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    enabled BOOLEAN NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS current_values (
                    bank_account_amount NUMERIC(14,2) NOT NULL,
                    cash_amount NUMERIC(14,2) NOT NULL,
                    range_start DATE NOT NULL,
                    range_end DATE NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS account_movements (
                    "date" DATE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    cash_balance NUMERIC(14,2) NOT NULL,
                    bank_account_balance NUMERIC(14,2) NOT NULL
                );
            """)


  # budget_repository.py

# ---------- RECURRING ITEMS ----------
def upsert_recurring_item(
    id: UUID,
    every: int,
    unit: str,
    category: str,
    description: str,
    date_from: date,
    date_to: Optional[date],
    type_: str,
    amount: Decimal,
    enabled: bool,
):
    """Insert or update a recurring item by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO budget.recurring_items (
                    id, every, unit, category, description,
                    date_from, date_to, "type", amount, enabled
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    every = EXCLUDED.every,
                    unit = EXCLUDED.unit,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    date_from = EXCLUDED.date_from,
                    date_to = EXCLUDED.date_to,
                    "type" = EXCLUDED."type",
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled
                """,
                (
                    str(id),
                    every,
                    unit,
                    category,
                    description,
                    date_from,
                    date_to,
                    type_,
                    amount,
                    enabled,
                ),
            )
        conn.commit()

    compute_and_replace_account_movements()


def delete_recurring_item(id: UUID) -> bool:
    """Delete recurring item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM budget.recurring_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()
    compute_and_replace_account_movements()

    return deleted


# ---------- SINGLE ITEMS ----------

def upsert_single_item(
    id: UUID,
    date_: date,
    category: str,
    description: str,
    type_: str,
    amount: Decimal,
    enabled: bool,
):
    """Insert or update a single (one-off) item by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO budget.single_items (
                    id, "date", category, description, "type", amount, enabled
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    "date" = EXCLUDED."date",
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    "type" = EXCLUDED."type",
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled
                """,
                (str(id), date_, category, description, type_, amount, enabled),
            )
        conn.commit()

    compute_and_replace_account_movements()


def delete_single_item(id: UUID) -> bool:
    """Delete single item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM budget.single_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()

    compute_and_replace_account_movements()

    return deleted


# ---------- CURRENT VALUES ----------

def update_current_values(
    bank_account_amount: Decimal,
    cash_amount: Decimal,
    range_start: date,
    range_end: date,
):
    """Overwrite the current values (table has only one row)."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM budget.current_values;
                INSERT INTO budget.current_values (
                    bank_account_amount, cash_amount, range_start, range_end
                )
                VALUES (%s, %s, %s, %s);
                """,
                (bank_account_amount, cash_amount, range_start, range_end),
            )
    conn.commit()

    compute_and_replace_account_movements()


@dataclass(frozen=True)
class AccountMovement:
    date: date
    category: str
    description: str
    amount: Decimal
    cash_balance: Decimal
    bank_account_balance: Decimal

def replace_account_movements(movements: Iterable[AccountMovement]) -> int:
    insert_sql = sql.SQL(
        "INSERT INTO account_movements "
        '("date", category, description, amount, cash_balance, bank_account_balance) '
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )

    rows = [(m.date, m.category, m.description, m.amount, m.cash_balance, m.bank_account_balance)
            for m in movements]

    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM account_movements")
            inserted = 0
            if rows:
                cur.executemany(insert_sql, rows)
                inserted = cur.rowcount
        conn.commit()

    return inserted




def add_months(d: date, n: int) -> date:
    """Add n months to d (keeps day when possible; clamps to end of month)."""
    year = d.year + (d.month - 1 + n) // 12
    month = (d.month - 1 + n) % 12 + 1
    # clamp day
    from calendar import monthrange
    max_day = monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def add_years(d: date, n: int) -> date:
    """Add n years to d (Feb 29 -> Feb 28 in non-leap years)."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        # Feb 29 -> Feb 28
        return d.replace(month=2, day=28, year=d.year + n)


def step_date(d: date, unit: str, every: int) -> date:
    if unit == "days":
        return d + timedelta(days=every)
    if unit == "weeks":
        return d + timedelta(weeks=every)
    if unit == "months":
        return add_months(d, every)
    if unit == "years":
        return add_years(d, every)
    raise ValueError(f"Unsupported unit: {unit}")


# ---------- Core function ----------

def compute_and_replace_account_movements() -> int:
    # --- Fetch all required data ---
    with get_cashflow_connection() as conn, conn.cursor() as cur:
        # current_values (single row)
        cur.execute(
            f"""SELECT bank_account_amount, cash_amount, range_start, range_end
                FROM {SCHEMA}.current_values"""
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("current_values is empty")
        bank_start, cash_start, range_start, range_end = row  # Decimals and dates

        # single items (enabled within window)
        cur.execute(
            f"""SELECT "date", category, description, "type", amount
                FROM {SCHEMA}.single_items
                WHERE enabled = TRUE
                  AND "date" BETWEEN %s AND %s""",
            (range_start, range_end),
        )
        single_rows = cur.fetchall()

        # recurring items (enabled, overlapping window)
        cur.execute(
            f"""SELECT every, unit, category, description, date_from, date_to, "type", amount
                FROM {SCHEMA}.recurring_items
                WHERE enabled = TRUE
                  AND date_from <= %s
                  AND (date_to IS NULL OR date_to >= %s)""",
            (range_end, range_start),
        )
        recurring_rows = cur.fetchall()

    # --- Build movements list (excluding the initial "Start") ---
    # Single items as movements
    pending: List[Tuple[date, str, str, str, Decimal]] = []
    for d, cat, desc, typ, amt in single_rows:
        pending.append((d, cat, desc, typ, Decimal(amt)))

    # Recurring occurrences within window
    for every, unit, cat, desc, d_from, d_to, typ, amt in recurring_rows:
        # Iterate from d_from until >= range_start
        occurrence = d_from
        while occurrence < range_start:
            occurrence = step_date(occurrence, unit, every)
        # Now generate occurrences inside window
        window_end = range_end
        last = d_to if d_to and d_to < window_end else window_end
        while occurrence <= last:
            pending.append((occurrence, cat, desc, typ, Decimal(amt)))
            occurrence = step_date(occurrence, unit, every)

    # --- Sort by date, then category/description for stable ordering ---
    pending.sort(key=lambda x: (x[0], x[1], x[2], x[4]))

    # --- Fold into running balances ---
    movements: List[AccountMovement] = []

    # Initial "Start" row (amount 0 on range_start)
    movements.append(
        AccountMovement(
            date=range_start,
            category="Start",
            description="Start",
            amount=Decimal("0.00"),
            cash_balance=Decimal(cash_start),
            bank_account_balance=Decimal(bank_start),
        )
    )

    cash_balance = Decimal(cash_start)
    bank_balance = Decimal(bank_start)

    for d, cat, desc, typ, amt in pending:
        if typ == "cash":
            cash_balance += amt
        else:
            # default to bank_account for anything else
            bank_balance += amt

        movements.append(
            AccountMovement(
                date=d,
                category=cat,
                description=desc,
                amount=amt,
                cash_balance=cash_balance,
                bank_account_balance=bank_balance,
            )
        )

    # --- Replace all rows in one shot ---
    return replace_account_movements(movements)
          
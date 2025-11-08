from __future__ import annotations
from connections import get_cashflow_connection
from uuid import UUID
import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple
from psycopg2 import sql


def init():
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS single_items (
                    id UUID PRIMARY KEY,
                    "date" DATE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    enabled BOOLEAN NOT NULL
                )
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS recurring_items (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    every INTEGER NOT NULL,
                    unit TEXT NOT NULL CHECK (unit IN ('day','week','month','year')),
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    date_from DATE NOT NULL,
                    date_to DATE NULL,
                    type TEXT NOT NULL CHECK (type IN ('Bank Account','Cash')),
                    amount NUMERIC(14,2) NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            cur.execute("""CREATE OR REPLACE VIEW recurring_items_projection AS
                WITH bounds AS (
                SELECT
                    r.id                         AS recurring_id,
                    r.every,
                    r.unit,
                    r.category,
                    r.description,
                    r.date_from,
                    r.date_to,
                    r.type,
                    r.amount,
                    /* stop at date_to, or 5 years from today if date_to is NULL */
                    COALESCE(r.date_to, (CURRENT_DATE + INTERVAL '5 years')::date) AS stop_date,
                    /* build the interval step based on unit + every */
                    CASE r.unit
                    WHEN 'day'   THEN make_interval(days   => r.every)
                    WHEN 'week'  THEN make_interval(days   => 7 * r.every)   -- (portable; avoids relying on weeks arg)
                    WHEN 'month' THEN make_interval(months => r.every)
                    WHEN 'year'  THEN make_interval(years  => r.every)
                    ELSE NULL
                    END AS step
                FROM recurring_items r
                WHERE r.enabled = TRUE
                ),
                expanded AS (
                SELECT
                    b.recurring_id,
                    b.category,
                    b.description,
                    b.type,
                    b.amount,
                    (gs)::date AS date,
                    ROW_NUMBER() OVER (PARTITION BY b.recurring_id ORDER BY (gs)::date) - 1 AS occurrence_index
                FROM bounds b
                CROSS JOIN LATERAL generate_series(
                    b.date_from::timestamp,
                    b.stop_date::timestamp,
                    b.step
                ) AS gs
                WHERE b.step IS NOT NULL
                    AND b.date_from <= b.stop_date
                )
                SELECT
                recurring_id,
                date,
                category,
                description,
                type,
                amount,
                occurrence_index
                FROM expanded
                ORDER BY date;
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS current_values (
                    bank_account_amount NUMERIC(14,2) NOT NULL,
                    cash_amount NUMERIC(14,2) NOT NULL,
                    range_start DATE NOT NULL,
                    range_end DATE NOT NULL
                );
            """)

            cur.execute("""CREATE OR REPLACE VIEW combined_items AS
                SELECT date, category, description, type, amount FROM recurring_items_projection
                    UNION
                SELECT date, category, description, type, amount FROM single_items WHERE enabled = TRUE
            """)

            cur.execute("""CREATE OR REPLACE VIEW account_movements AS
                WITH cv AS (
                SELECT *
                FROM current_values
                LIMIT 1
                )
                SELECT
                c.date,
                c.category,
                c.description,
                c.type,
                c.amount,
                -- opening cash balance + running cash deltas from range_start
                cv.cash_amount
                    + SUM(CASE WHEN c.type = 'Cash' THEN c.amount ELSE 0 END)
                        OVER (ORDER BY c.date)     AS "Cash",
                -- opening bank balance + running bank deltas from range_start
                cv.bank_account_amount
                    + SUM(CASE WHEN c.type = 'Bank Account' THEN c.amount ELSE 0 END)
                        OVER (ORDER BY c.date)     AS "BankAccount"
                
                FROM combined_items c
                CROSS JOIN cv
                WHERE c.date BETWEEN cv.range_start AND cv.range_end
                ORDER BY c.date;
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


def delete_recurring_item(id: UUID) -> bool:
    """Delete recurring item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM budget.recurring_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()

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


def fetch_account_movements() -> List[Dict[str, Any]]:
    sql = """
        SELECT
            date,
            category,
            description,
            type,
            amount,
            "Cash",
            "Bank Account"
        FROM account_movements
        ORDER BY date;
    """
    with get_cashflow_connection() as conn:
        with conn.cursor(row_factory=psycopg2.rows.dict_row) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
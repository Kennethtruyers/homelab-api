from __future__ import annotations
from connections import get_cashflow_connection
from uuid import UUID
import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import psycopg2
from typing import Optional, List, Dict, Any
from datetime import date, datetime


def init():
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL, 
                    date DATE NOT NULL,
                    amount NUMERIC(14,2) NOT NULL	
                );
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS single_items (
                    id UUID PRIMARY KEY,
                    "date" DATE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    enabled BOOLEAN NOT NULL,
					account_id UUID NULL,
    				CONSTRAINT fk_single_items_account
        			FOREIGN KEY (account_id)
        			REFERENCES accounts(id)
        			ON DELETE SET NULL
					);
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
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    account_id UUID NULL,
                    CONSTRAINT fk_recurring_items_account
                        FOREIGN KEY (account_id)
                        REFERENCES accounts(id)
                        ON DELETE SET NULL
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
                        r.account_id,
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
                        b.account_id,
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
                    account_id,
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
                    SELECT date, category, description, type, amount, account_id FROM recurring_items_projection
                        UNION
                    SELECT date, category, description, type, amount, account_id FROM single_items WHERE enabled = TRUE
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
                            OVER (ORDER BY c.date)     AS "cash",
                    -- opening bank balance + running bank deltas from range_start
                    cv.bank_account_amount
                        + SUM(CASE WHEN c.type = 'Bank Account' THEN c.amount ELSE 0 END)
                            OVER (ORDER BY c.date)     AS "bank"
                    
                    FROM combined_items c
                    CROSS JOIN cv
                    WHERE c.date BETWEEN cv.range_start AND cv.range_end
                    ORDER BY c.date;
            """)

            cur.execute("""CREATE OR REPLACE VIEW account_movements_by_account AS
                    WITH movements AS (
                    SELECT
                        ci.date,
                        ci.category,
                        ci.description,
                        ci.account_id,
                        ci.amount
                    FROM combined_items ci
                    JOIN accounts a
                        ON a.id = ci.account_id
                    AND ci.account_id IS NOT NULL
                    AND ci.date >= a.date             -- only movements on/after the account’s anchor date
                    ),
                    opening AS (
                    -- one synthetic opening row per account at its anchor date
                    SELECT
                        a.date       AS date,
                        'Opening Balance'::text AS category,
                        a.name       AS description,
                        a.id         AS account_id,
                        0::numeric   AS amount,          -- delta 0; opening goes in a separate column
                        a.amount     AS opening_amount
                    FROM accounts a
                    ),
                    unioned AS (
                    SELECT m.date, m.category, m.description, m.account_id, m.amount, NULL::numeric AS opening_amount
                    FROM movements m
                    UNION ALL
                    SELECT o.date, o.category, o.description, o.account_id, o.amount, o.opening_amount
                    FROM opening o
                    )
                    SELECT
                    u.date,
                    u.category,
                    u.description,
                    u.account_id,
                    u.amount,
                    /* running balance per account = opening + cumulative deltas */
                    COALESCE(MAX(u.opening_amount) OVER (PARTITION BY u.account_id), 0)
                        + SUM(u.amount) OVER (
                            PARTITION BY u.account_id
                            ORDER BY u.date, u.category, u.description
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS balance
                    FROM unioned u
                    ORDER BY u.date, u.account_id, u.category, u.description;
            """)

# ---------- ACCOUNTS -----------------
def upsert_account(
    id: UUID,
    name: str,
    date: date,
    amount: Decimal
):
    """Insert or update an account by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (
                    id, name, date, amount
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    date = EXCLUDED.date,
                    amount = EXCLUDED.amount
                """,
                (
                    str(id),
                    name,
                    date,
                    amount
                ),
            )
        conn.commit()


def fetch_accounts() -> List[Dict[str, Any]]:
    sql = """SELECT id, name, date, amount FROM accounts;"""
    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()


# ---------- RECURRING ITEMS ----------
def upsert_recurring_item(
    id: UUID,
    every: int,
    unit: str,
    category: str,
    description: str,
    dateFrom: date,
    dateTo: Optional[date],
    type_: str,
    amount: Decimal,
    enabled: bool,
    account_id: UUID
):
    """Insert or update a recurring item by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recurring_items (
                    id, every, unit, category, description,
                    date_from, date_to, "type", amount, enabled, account_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    every = EXCLUDED.every,
                    unit = EXCLUDED.unit,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    date_from = EXCLUDED.date_from,
                    date_to = EXCLUDED.date_to,
                    "type" = EXCLUDED."type",
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled,
                    account_id = EXCLUDED.account_id
                """,
                (
                    str(id),
                    every,
                    unit,
                    category,
                    description,
                    dateFrom,
                    dateTo,
                    type_,
                    amount,
                    enabled,
                    str(account_id)
                ),
            )
        conn.commit()


def delete_recurring_item(id: UUID) -> bool:
    """Delete recurring item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recurring_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()

    return deleted

def fetch_recurring_items(account_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id,
            every,
            unit,
            category,
            description,
            date_from AS "dateFrom",
            date_to AS "dateTo",
            type,
            amount,
            enabled,
            account_id AS "accountId"
        FROM recurring_items
    """
    params = []
    if account_id is not None:
        sql += " WHERE account_id = %s"
        params.append(account_id)

    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()




# ---------- SINGLE ITEMS ----------

def upsert_single_item(
    id: UUID,
    date_: date,
    category: str,
    description: str,
    type_: str,
    amount: Decimal,
    enabled: bool,
    account_id: UUID
):
    """Insert or update a single (one-off) item by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO single_items (
                    id, "date", category, description, "type", amount, enabled, account_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    "date" = EXCLUDED."date",
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    "type" = EXCLUDED."type",
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled,
                    account_id = EXCLUDED.account_id
                """,
                (str(id), date_, category, description, type_, amount, enabled, str(account_id)),
            )
        conn.commit()


def delete_single_item(id: UUID) -> bool:
    """Delete single item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM single_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()

    compute_and_replace_account_movements()

    return deleted

def fetch_single_items(account_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id,
            date,
            category,
            description,
            type,
            amount,
            enabled,
            account_id as "accountId"
        FROM single_items
    """

    params = []
    if account_id is not None:
        sql += " WHERE account_id = %s"
        params.append(account_id)

    sql += " ORDER BY date"

    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

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
                DELETE FROM current_values;
                INSERT INTO current_values (
                    bank_account_amount, cash_amount, range_start, range_end
                )
                VALUES (%s, %s, %s, %s);
                """,
                (bank_account_amount, cash_amount, range_start, range_end),
            )
    conn.commit()      


def fetch_account_movements(account_id: Optional[str] = None,
                            until: Optional[date] = None) -> List[Dict[str, Any]]:

    # Pick view + fields
    if account_id is not None:
        view_name = "account_movements_by_account"
        fields = "date, category, description, account_id, amount, balance"
    else:
        view_name = "account_movements"
        fields = "date, category, description, type, amount, cash, bank"

    sql = f"SELECT {fields} FROM {view_name}"
    where = []
    params: list = []

    # Conditions
    if account_id is not None:
        where.append("account_id = %s")
        params.append(account_id)

    if until is not None:
        where.append("date < %s")
        params.append(until)

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY date"

    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()



def fetch_current_values() -> List[Dict[str, Any]]:
    sql = """
        SELECT
            bank_account_amount as "bank",
            cash_amount as "cash",
            range_start as "start",
            range_end as "end"
        FROM current_values;
    """
    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()
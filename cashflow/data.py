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
                    endDate DATE NOT NULL,
                    amount NUMERIC(14,2) NOT NULL	
                );
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS single_items (
                    id UUID PRIMARY KEY,
                    "date" DATE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('absolute','percent')),
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
                    kind TEXT NOT NULL CHECK (kind IN ('absolute','percent')),
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
                        r.kind,
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
                        b.kind,
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
                    kind,
                    amount,
                    account_id,
                    occurrence_index
                    FROM expanded
                    ORDER BY date;
            """)

            cur.execute("""CREATE OR REPLACE VIEW combined_items AS
                    SELECT date, category, description, amount, account_id, kind FROM recurring_items_projection
                        UNION
                    SELECT date, category, description, amount, account_id, kind FROM single_items WHERE enabled = TRUE
            """)

            cur.execute("""CREATE OR REPLACE VIEW account_movements_by_account AS
                            WITH RECURSIVE
                            anchors AS (
                            SELECT
                                a.id   AS account_id,
                                a.name AS account_name,
                                a.date AS anchor_date,
                                a.amount::numeric AS opening_balance
                            FROM accounts a
                            ),
                            movements AS (
                            SELECT
                                ci.date,
                                ci.category,
                                ci.description,
                                ci.account_id,
                                ci.amount::numeric,
                                ci.kind::text,          -- 'absolute' | 'percent'
                                1 AS ord
                            FROM combined_items ci
                            JOIN anchors an
                                ON an.account_id = ci.account_id
                            AND ci.account_id IS NOT NULL
                            AND ci.date >= an.anchor_date
                            ),
                            opening AS (
                            -- synthetic opening row per account at its anchor date
                            SELECT
                                an.anchor_date AS date,
                                'Opening Balance'::text AS category,
                                an.account_name AS description,
                                an.account_id,
                                0::numeric AS amount,   -- no delta
                                'absolute'::text AS kind,
                                0 AS ord
                            FROM anchors an
                            ),
                            unioned AS (
                            SELECT date, category, description, account_id, amount, kind, ord FROM movements
                            UNION ALL
                            SELECT date, category, description, account_id, amount, kind, ord FROM opening
                            ),
                            sequenced AS (
                            SELECT
                                u.*,
                                ROW_NUMBER() OVER (
                                PARTITION BY u.account_id
                                ORDER BY u.date, u.ord, u.category, u.description
                                ) AS rn
                            FROM unioned u
                            ),
                            rec AS (
                            -- seed: first row per account with the opening balance
                            SELECT
                                s.account_id, s.rn, s.date, s.category, s.description, s.kind, s.amount,
                                an.opening_balance AS balance
                            FROM sequenced s
                            JOIN anchors an ON an.account_id = s.account_id
                            WHERE s.rn = 1

                            UNION ALL

                            -- step: apply subsequent rows in order
                            SELECT
                                s.account_id, s.rn, s.date, s.category, s.description, s.kind, s.amount,
                                CASE
                                WHEN s.kind = 'percent'
                                    THEN r.balance *  (1 + s.amount/100)   -- use (1 + s.amount/100.0) if you store 5 for 5%
                                ELSE r.balance + s.amount
                                END AS balance
                            FROM rec r
                            JOIN sequenced s
                                ON s.account_id = r.account_id
                            AND s.rn         = r.rn + 1
                            )
                            SELECT
                            r.date,
                            r.category,
                            r.description,
                            r.account_id,
							CASE
                                WHEN r.kind = 'percent'
                                    THEN r.balance - (r.balance /  (1 + r.amount/100))
                                ELSE r.amount
							END AS amount,
                            r.kind,
                            r.balance
                            FROM rec r
                            ORDER BY r.date, r.account_id, r.category, r.description;
            """)

# ---------- ACCOUNTS -----------------
def upsert_account(
    id: UUID,
    name: str,
    date: date,
    endDate: date,
    amount: Decimal):
    """Insert or update an account by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (
                    id, name, date, enddate, amount
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    date = EXCLUDED.date,
                    enddate = EXCLUDED.endDate,
                    amount = EXCLUDED.amount
                """,
                (
                    str(id),
                    name,
                    date,
                    endDate,
                    amount
                ),
            )
        conn.commit()

def fetch_accounts() -> List[Dict[str, Any]]:
    sql = """SELECT id, name, date, enddate, amount FROM accounts;"""
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
    kind: str,
    amount: Decimal,
    enabled: bool,
    account_id: UUID):
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recurring_items (
                    id, every, unit, category, description,
                    date_from, date_to, kind, amount, enabled, account_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    every = EXCLUDED.every,
                    unit = EXCLUDED.unit,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    date_from = EXCLUDED.date_from,
                    date_to = EXCLUDED.date_to,
                    kind = EXCLUDED.kind,
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
                    kind,
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
            kind,
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
    kind: str,
    amount: Decimal,
    enabled: bool,
    account_id: UUID):
    """Insert or update a single (one-off) item by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO single_items (
                    id, "date", category, description, kind, amount, enabled, account_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    "date" = EXCLUDED."date",
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    kind = EXCLUDED.kind,
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled,
                    account_id = EXCLUDED.account_id
                """,
                (str(id), date_, category, description, kind, amount, enabled, str(account_id)),
            )
        conn.commit()

def delete_single_item(id: UUID) -> bool:
    """Delete single item by ID. Returns True if something was deleted."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM single_items WHERE id = %s", (str(id),))
            deleted = cur.rowcount > 0
        conn.commit()

    return deleted

def fetch_single_items(account_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id,
            date,
            category,
            description,
            kind,
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

# ---------- Account movements ----------
def fetch_account_movements(account_id: str, until: Optional[date] = None) -> List[Dict[str, Any]]:

    sql = "SELECT date, category, description, account_id, amount, balance FROM account_movements_by_account"
    where = ["account_id = %s"]
    params: list = [account_id]

    if until is not None:
        where.append("date < %s")
        params.append(until)

    sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date"

    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
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
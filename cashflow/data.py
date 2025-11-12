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
                    amount NUMERIC(14,2) NOT NULL,
                    type string,
                    liquid bool	
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
                        COALESCE(r.date_to, a.enddate) AS stop_date,
                        /* build the interval step based on unit + every */
                        CASE r.unit
                        WHEN 'day'   THEN make_interval(days   => r.every)
                        WHEN 'week'  THEN make_interval(days   => 7 * r.every)   -- (portable; avoids relying on weeks arg)
                        WHEN 'month' THEN make_interval(months => r.every)
                        WHEN 'year'  THEN make_interval(years  => r.every)
                        ELSE NULL
                        END AS step
                    FROM recurring_items r
					INNER JOIN accounts a
					ON a.id = r.account_id
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
                        (gs)::date AS date
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
                    account_id
                    FROM expanded
                    ORDER BY date;
            """)

            cur.execute("""CREATE OR REPLACE VIEW combined_items AS
                SELECT date, category, description, amount, account_id, kind FROM recurring_items_projection
                    UNION
                SELECT date, category, description, amount, account_id, kind FROM single_items WHERE enabled = TRUE;
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
                        s.account_id, s.rn, s.date, s.category, s.description, s.kind, an.opening_balance as amount,
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
                    r.balance,
                    a.type,
                    a.liquid
                    FROM rec r
                    INNER JOIN accounts a
                    ON a.id = r.account_id
                    ORDER BY r.date, r.account_id, r.category, r.description;
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS scenarios (
                id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                description TEXT
                );
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS recurring_overrides (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                scenario_id UUID NOT NULL REFERENCES scenarios(id),
                op TEXT NOT NULL CHECK (op IN ('add','replace')),

                -- target for replace; NULL for add
                target_recurring_id UUID NULL REFERENCES recurring_items(id),

                -- fields allowed to change on replace (or required for add)
                every INTEGER,
                unit  TEXT CHECK (unit IN ('day','week','month','year')),
                amount NUMERIC(14,2),
                date_from DATE,
                date_to DATE,
                enabled BOOLEAN,

                -- for ADD you must also supply these immutable fields:
                category TEXT,
                description TEXT,
                kind TEXT CHECK (kind IN ('absolute','percent')),
                account_id UUID
                );
            """)

            cur.execute("""CREATE TABLE IF NOT EXISTS single_overrides (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                scenario_id UUID NOT NULL REFERENCES scenarios(id),
                op TEXT NOT NULL CHECK (op IN ('add','replace')),

                -- target for replace; NULL for add
                target_single_id UUID NULL REFERENCES single_items(id),

                -- fields allowed on replace (or required on add)
                "date" DATE,
                amount NUMERIC(14,2),
                enabled BOOLEAN,

                -- for ADD you must also supply these immutable fields:
                category TEXT,
                description TEXT,
                kind TEXT CHECK (kind IN ('absolute','percent')),
                account_id UUID
                );
            """)

            cur.execute("""CREATE OR REPLACE FUNCTION recurring_items_projection_for(scenario_name TEXT)
                RETURNS TABLE(
                recurring_id UUID,
                date DATE,
                category TEXT,
                description TEXT,
                kind TEXT,
                amount NUMERIC(14,2),
                account_id UUID
                )
                LANGUAGE sql
                AS $$
                WITH
                s AS (SELECT id FROM scenarios WHERE name = scenario_name),

                -- Base + REPLACE (immutable cols preserved)
                base_modified AS (
                SELECT
                    r.id,
                    COALESCE(ro.every, r.every) AS every,
                    COALESCE(ro.unit,  r.unit)  AS unit,
                    r.category,
                    r.description,
                    COALESCE(ro.date_from, r.date_from) AS date_from,
                    COALESCE(ro.date_to,   r.date_to)   AS date_to,
                    r.kind,
                    COALESCE(ro.amount, r.amount) AS amount,
                    r.account_id,
                    COALESCE(ro.enabled, r.enabled) AS enabled
                FROM recurring_items r
                LEFT JOIN recurring_overrides ro
                    ON ro.target_recurring_id = r.id
                AND ro.op = 'replace'
                AND ro.scenario_id = (SELECT id FROM s)
                WHERE TRUE
                ),

                -- ADD rows (all fields required)
                adds AS (
                SELECT
                    gen_random_uuid() AS id,
                    ro.every, ro.unit, ro.category, ro.description,
                    ro.date_from, ro.date_to, ro.kind, ro.amount, ro.account_id,
                    COALESCE(ro.enabled, TRUE) AS enabled
                FROM recurring_overrides ro
                JOIN s ON s.id = ro.scenario_id
                WHERE ro.op = 'add'
                ),

                -- unified source
                recurring_source AS (
                SELECT * FROM base_modified
                UNION ALL
                SELECT * FROM adds
                ),

                bounds AS (
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
                    COALESCE(r.date_to, a.enddate) AS stop_date,
                    CASE r.unit
                    WHEN 'day'   THEN make_interval(days   => r.every)
                    WHEN 'week'  THEN make_interval(days   => 7 * r.every)
                    WHEN 'month' THEN make_interval(months => r.every)
                    WHEN 'year'  THEN make_interval(years  => r.every)
                    ELSE NULL
                    END AS step
                FROM recurring_source r
                INNER JOIN accounts a ON a.id = r.account_id
                WHERE r.enabled = TRUE
                ),
                expanded AS (
                SELECT
                    b.recurring_id,
                    (gs)::date AS date,
                    b.category,
                    b.description,
                    b.kind,
                    b.amount,
                    b.account_id
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
                recurring_id, date, category, description, kind, amount, account_id
                FROM expanded
                ORDER BY date;
            """)

            cur.execute("""CREATE OR REPLACE FUNCTION combined_items_for(scenario_name TEXT)
                RETURNS TABLE(
                date DATE,
                category TEXT,
                description TEXT,
                amount NUMERIC(14,2),
                account_id UUID,
                kind TEXT
                )
                LANGUAGE sql
                AS $$
                WITH
                s AS (SELECT id FROM scenarios WHERE name = scenario_name),

                base_modified AS (
                SELECT
                    si.id,
                    COALESCE(so."date", si."date") AS "date",
                    si.category,
                    si.description,
                    si.kind,
                    COALESCE(so.amount, si.amount) AS amount,
                    si.account_id,
                    COALESCE(so.enabled, si.enabled) AS enabled
                FROM single_items si
                LEFT JOIN single_overrides so
                    ON so.target_single_id = si.id
                AND so.op = 'replace'
                AND so.scenario_id = (SELECT id FROM s)
                ),
                adds AS (
                SELECT
                    gen_random_uuid() AS id,
                    so."date", so.category, so.description, so.kind,
                    so.amount, so.account_id,
                    COALESCE(so.enabled, TRUE) AS enabled
                FROM single_overrides so
                JOIN s ON s.id = so.scenario_id
                WHERE so.op = 'add'
                ),
                single_source AS (
                SELECT id, "date", category, description, kind, amount, account_id, enabled FROM base_modified
                UNION ALL
                SELECT id, "date", category, description, kind, amount, account_id, enabled FROM adds
                )
                SELECT date, category, description, amount, account_id, kind
                FROM (
                SELECT date, category, description, amount, account_id, kind
                FROM recurring_items_projection_for(scenario_name)
                UNION ALL
                SELECT "date", category, description, amount, account_id, kind
                FROM single_source
                WHERE enabled = TRUE
                ) q
                ORDER BY date;
            """)

            cur.execute("""CREATE OR REPLACE FUNCTION account_movements_by_account_for(scenario_name TEXT)
                RETURNS TABLE(
                date DATE,
                category TEXT,
                description TEXT,
                account_id UUID,
                amount NUMERIC(14,2),
                kind TEXT,
                balance NUMERIC(14,2),
                type TEXT,
                liquid BOOLEAN
                )
                LANGUAGE sql
                AS $$
                WITH RECURSIVE
                anchors AS (
                SELECT a.id AS account_id, a.name AS account_name, a.date AS anchor_date,
                        a.amount::numeric AS opening_balance
                FROM accounts a
                ),
                movements AS (
                SELECT
                    ci.date, ci.category, ci.description, ci.account_id,
                    ci.amount::numeric, ci.kind::text, 1 AS ord
                FROM combined_items_for(scenario_name) ci
                JOIN anchors an ON an.account_id = ci.account_id
                WHERE ci.account_id IS NOT NULL
                    AND ci.date >= an.anchor_date
                ),
                opening AS (
                SELECT an.anchor_date AS date, 'Opening Balance'::text AS category,
                        an.account_name AS description, an.account_id,
                        0::numeric AS amount, 'absolute'::text AS kind, 0 AS ord
                FROM anchors an
                ),
                unioned AS (
                SELECT date, category, description, account_id, amount, kind, ord FROM movements
                UNION ALL
                SELECT date, category, description, account_id, amount, kind, ord FROM opening
                ),
                sequenced AS (
                SELECT u.*,
                        ROW_NUMBER() OVER (PARTITION BY u.account_id ORDER BY u.date, u.ord, u.category, u.description) AS rn
                FROM unioned u
                ),
                rec AS (
                SELECT s.account_id, s.rn, s.date, s.category, s.description, s.kind,
                        an.opening_balance AS amount, an.opening_balance AS balance
                FROM sequenced s
                JOIN anchors an ON an.account_id = s.account_id
                WHERE s.rn = 1
                UNION ALL
                SELECT s.account_id, s.rn, s.date, s.category, s.description, s.kind, s.amount,
                        CASE WHEN s.kind = 'percent'
                            THEN r.balance * (1 + s.amount/100)
                            ELSE r.balance + s.amount
                        END AS balance
                FROM rec r
                JOIN sequenced s ON s.account_id = r.account_id AND s.rn = r.rn + 1
                )
                SELECT
                r.date,
                r.category,
                r.description,
                r.account_id,
                CASE WHEN r.kind = 'percent'
                    THEN r.balance - (r.balance / (1 + r.amount/100))
                    ELSE r.amount
                END AS amount,
                r.kind,
                r.balance,
                a.type,
                a.liquid
                FROM rec r
                JOIN accounts a ON a.id = r.account_id
                ORDER BY r.date, r.account_id, r.category, r.description;
            """)

# ---------- ACCOUNTS -----------------
def upsert_account(
    id: UUID,
    name: str,
    date: date,
    endDate: date,
    amount: Decimal,
    type: str,
    liquid : bool):
    """Insert or update an account by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (
                    id, name, date, enddate, amount, type, liquid
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    date = EXCLUDED.date,
                    enddate = EXCLUDED.endDate,
                    amount = EXCLUDED.amount,
                    type = EXCLUDED.type,
                    liquid = EXCLUDED.liquid
                """,
                (
                    str(id),
                    name,
                    date,
                    endDate,
                    amount,
                    type,
                    liquid
                ),
            )
        conn.commit()

def fetch_accounts() -> List[Dict[str, Any]]:
    sql = """SELECT id, name, date, enddate, amount, type, liquid FROM accounts;"""
    with get_cashflow_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()

# ---------- Scenarios -----------------
def upsert_scenario(
    id: UUID,
    name: str,
    description: str):
    """Insert or update a scenario by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scenarios (
                    id, name, description
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description
                """,
                (
                    str(id),
                    name,
                    description
                ),
            )
        conn.commit()

def fetch_scenarios() -> List[Dict[str, Any]]:
    sql = """SELECT id, name, description FROM scenarios;"""
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

def upsert_recurring_item_override(
    id: UUID,
    scenarioId: UUID,
    op: str,
    targetRecurringId: UUID,
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
                INSERT INTO recurring_overrides (
                    id, scenario_id, op, target_recurring_id, every, unit, amount, date_from, date_to, enabled, category, description, kind, account_id)
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    scenario_id = EXCLUDED.scenario_id,
                    op = EXCLUDED.op,
                    target_recurring_id = EXCLUDED.target_recurring_id,
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
                    str(scenarioId),
                    op,
                    str(targetRecurringId),
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
            cur.execute("DELETE FROM recurring_overrides WHERE target_recurring_id = %s", (str(id),))
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

def fetch_recurring_items_overrides(account_id: Optional[str] = None, scenario_id : Optional(str) = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT
           id, scenario_id as scenarioId, op, target_recurring_id as targetRecurringId, every, unit, amount, 
            date_from as "dateFrom", date_to as "dateTo", enabled, category, description, kind, account_id as "accountId"
        FROM recurring_overrides
    """

    where_clause, params = build_where_clause({
        "account_id": account_id,
        "scenario_id": scenario_id
    })

    sql += where_clause
    sql += " ORDER BY date"

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

def upsert_single_item_override(
    id: UUID,
    scenario_id: UUID,
    op: str,
    targetSingleId: UUID,
    date_: date,
    category: str,
    description: str,
    kind: str,
    amount: Decimal,
    enabled: bool,
    account_id: UUID):
    """Insert or update a single (one-off) override by ID."""
    with get_cashflow_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO single_overrides (
                    id, "date", category, description, kind, amount, enabled, account_id, scenario_id, op, target_single_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    "date" = EXCLUDED."date",
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    kind = EXCLUDED.kind,
                    amount = EXCLUDED.amount,
                    enabled = EXCLUDED.enabled,
                    account_id = EXCLUDED.account_id,
                    scenario_id = EXCLUDED.scenario_id,
                    op = EXCLUDED.op,
                    target_single_id = EXCLUDED.target_single_id
                """,
                (str(id), date_, category, description, kind, amount, enabled, str(account_id), str(scenario_id), op, str(targetSingleId)),
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

def fetch_single_items_overrides(account_id: Optional[str] = None, scenario_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            id,
            date,
            category,
            description,
            kind,
            amount,
            enabled,
            account_id as "accountId",
            target_single_id as targetSingleId,
            op,
            scenario_id as "scenarioId"
        FROM single_overrides
    """

    where_clause, params = build_where_clause({
        "account_id": account_id,
        "scenario_id": scenario_id
    })

    sql += where_clause
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

def build_where_clause(conditions):
    parts, params = [], []
    for field, (op, value) in conditions.items():
        if value is not None:
            parts.append(f"{field} {op} %s")
            params.append(value)
    return (" WHERE " + " AND ".join(parts)) if parts else "", params
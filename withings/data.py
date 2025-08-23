from connections import get_connection
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Iterable, Tuple
import psycopg2.extras as extras

def init():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS withings_tokens (
                    id TEXT PRIMARY KEY,
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_at TIMESTAMPTZ
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS withings_measures (
                    -- core identity (composite PK)
                    "timestamp" BIGINT NOT NULL,
                    "key"       TEXT   NOT NULL,
                    fm          INTEGER NOT NULL DEFAULT -1,   -- None -> -1 sentinel
                    algo        INTEGER NOT NULL DEFAULT -1,   -- None -> -1 sentinel

                    -- payload
                    "datetime"  TIMESTAMPTZ,
                    "value"     DOUBLE PRECISION NOT NULL,

                    PRIMARY KEY ("timestamp", "key", fm, algo)
                );
            """)

def upsert_measures(rows: Iterable[Dict[str, Any]]) -> None:
    values = [_normalize_row(r) for r in rows]

    sql = """
    INSERT INTO withings_measures ("timestamp","key",fm,algo,"datetime","value")
    VALUES %s
    ON CONFLICT ("timestamp","key",fm,algo) DO UPDATE
      SET "datetime" = EXCLUDED."datetime",
          "value"    = EXCLUDED."value";
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            extras.execute_values(cur, sql, values, template="(%s,%s,%s,%s,%s,%s)", page_size=1000)
        conn.commit()

def upsert_tokens(access_token: str, refresh_token: str, expires_in: int, user_id: str = "default"):
    """Insert or update tokens for a user"""
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO withings_tokens (id, access_token, refresh_token, expires_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at   = EXCLUDED.expires_at
            """, (user_id, access_token, refresh_token, expires_at))

def get_tokens(user_id: str = "default"):
    """Fetch tokens for a user"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT access_token, refresh_token, expires_at FROM withings_tokens WHERE id = %s", (user_id,))
            row = cur.fetchone()

            
            if row:
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "expires_at": row[2]
                }
            return None

def _parse_iso8601(s: str | None) -> datetime | None:
    if not s:
        return None
    # Accept "Z" suffix as UTC
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        # Ensure timezone-aware UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None

def _normalize_row(row: Dict[str, Any]) -> Tuple[int, str, int, int, datetime, float]:
    ts = int(row["timestamp"])
    key = str(row["key"])
    fm = row.get("fm", -1)
    algo = row.get("algo", -1)
    fm = -1 if fm is None else int(fm)
    algo = -1 if algo is None else int(algo)

    # Prefer provided ISO datetime; otherwise derive from timestamp
    dt = _parse_iso8601(row.get("datetime"))
    if dt is None:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

    value = float(row["value"])
    return ts, key, fm, algo, dt, value
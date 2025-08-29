from connections import get_connection, get_influx_client
from datetime import datetime, timedelta, timezone
from typing import Iterable, Dict, Any, List, DefaultDict, Tuple
from collections import defaultdict
import psycopg2.extras as extras
import psycopg2
from psycopg2.extras import DictCursor
import math
import re

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
                    userid      text NOT NULL,

                    -- payload
                    "datetime"  TIMESTAMPTZ,
                    "value"     DOUBLE PRECISION NOT NULL,

                    PRIMARY KEY ("timestamp", "key", userid)
                );
            """)

def upsert_measures(rows: Iterable[Dict[str, Any]], userid : str, startdate: int, enddate: int) -> None:
    upsert_measures_sql(rows, userid, startdate, enddate)
    upsert_measures_influx(rows, userid, startdate, enddate)

def upsert_measures_sql(rows: Iterable[Dict[str, Any]], userid : str, startdate: int, enddate: int) -> None:
    base_values = [_normalize_row(r) for r in rows]
    values = [(userid, *v) for v in base_values]

    delete_sql = """
        DELETE FROM withings_measures
        WHERE userid = %s
        AND "timestamp" BETWEEN %s AND %s;
    """

    insert_sql = """
    INSERT INTO withings_measures (userid, "timestamp","key","datetime","value")
    VALUES %s
    ON CONFLICT (userid, "timestamp","key") DO UPDATE
      SET "datetime" = EXCLUDED."datetime",
          "value"    = EXCLUDED."value";
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
             cur.execute(delete_sql, (userid, startdate, enddate))

             if values:
                extras.execute_values(cur, insert_sql, values, template="(%s,%s,%s,%s,%s,%s,%s)", page_size=1000)

        conn.commit()

from typing import Iterable, Dict, Any, List, DefaultDict
from collections import defaultdict
import math, re

def _normalize_field_name(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

def upsert_measures_influx(
    rows: Iterable[Dict[str, Any]],
    userid: str,
    startdate: int,
    enddate: int,
    *,
    delete_window: bool = True,
    retention_policy: str = "autogen",
    batch_size: int = 5000,
) -> None:
    """
    InfluxDB 1.8 upsert: DELETE window for userid (optional), then write points.

    Measurement: withings
      tags: userid
      fields: one per key
      time: r["timestamp"] (seconds)
    """
    client = get_influx_client("fitness")

    if delete_window:
        # DELETE: InfluxQL needs RFC3339 times; end is exclusive, so add 1s
        start_rfc = _rfc3339_utc(startdate)
        end_rfc   = _rfc3339_utc(enddate + 1)
        delete_q  = (
            f'DELETE FROM "withings" '
            f'WHERE time >= \'{start_rfc}\' AND time < \'{end_rfc}\' '
            f'AND "userid" = \'{userid}\''
        )
        client.query(delete_q)

    # Group into one point per timestamp
    grouped: DefaultDict[int, Dict[str, float]] = defaultdict(dict)

    for r in rows:
        ts_raw = r.get("timestamp")
        key_raw = r.get("key")
        val_raw = r.get("value")
        if ts_raw is None or key_raw is None or val_raw is None:
            continue
        try:
            ts = int(ts_raw)
            val = float(val_raw)
        except (ValueError, TypeError):
            continue
        if math.isnan(val) or math.isinf(val):
            continue

        field = _normalize_field_name(key_raw)

        if not field:
            continue

        grouped[ts][field] = val

    # Emit points
    points: List[Dict[str, Any]] = []
    for ts, fields in grouped.items():
        if not fields:
            continue
        points.append({
            "measurement": "withings",
            "tags": {"userid": userid},
            "time": ts,
            "fields": fields,
        })

    if points:
        client.write_points(
            points,
            time_precision="s",
            retention_policy=retention_policy,
            batch_size=batch_size,
        )



def full_resync_measures_from_postgres() -> None:
    influx = get_influx_client("fitness")
    delete_q = 'DELETE FROM "withings"'  # all users (whole measurement in RP)
    influx.query(delete_q)

    # 2) Stream from Postgres
    with get_connection() as conn:
        with conn.cursor(name="withings_stream", cursor_factory=DictCursor) as cur:
            base_sql = """
                SELECT 
                    CAST(timestamp AS BIGINT)     AS timestamp,
                    key::text                     AS key,
                    value::float                  AS value,
                    userid::text                  AS userid
                FROM withings_measures
                ORDER BY userid, timestamp
            """
            

            cur.execute(base_sql)

            buffer: list[dict[str, any]] = []
            current_user: str | None = None

            def flush_buffer(u: str | None):
                if not buffer:
                    return
                # Since we wiped Influx already, skip the delete window inside the writer
                # We still need start/end to satisfy signature; values are ignored with delete_window=False
                upsert_measures_influx(
                    rows=buffer,
                    userid=u,               # u is not None here
                    startdate=0,
                    enddate=0,
                    delete_window=False,
                    retention_policy="autogen",
                )
                buffer.clear()

            for row in cur:
                u = row["userid"]
                if current_user is None:
                    current_user = u
                # If we switch users, flush the prior buffer so tagging is correct
                if u != current_user:
                    flush_buffer(current_user)
                    current_user = u

                buffer.append({
                    "timestamp": row["timestamp"],
                    "key": row["key"],
                    "value": row["value"],
                })

                if len(buffer) >= 50_000:
                    flush_buffer(current_user)

            # Flush last chunk
            flush_buffer(current_user)


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

def _rfc3339_utc(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _normalize_row(row: Dict[str, Any]) -> Tuple[int, str, int, int, datetime, float]:
    ts = int(row["timestamp"])
    key = str(row["key"])
    
    # Prefer provided ISO datetime; otherwise derive from timestamp
    dt = _parse_iso8601(row.get("datetime"))
    if dt is None:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

    value = float(row["value"])
    return ts, key, dt, value

def _normalize_field_name(s: str) -> str:
    """
    Make a safe-ish InfluxDB field key: lowercase, strip, replace non-word with underscores,
    collapse repeats, strip leading/trailing underscores.
    """
    s = str(s).strip().lower()
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")
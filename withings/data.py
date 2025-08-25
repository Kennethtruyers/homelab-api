from connections import get_connection, get_influx_client
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
                    userid      text NOT NULL,
                    fm          INTEGER NOT NULL DEFAULT -1,   -- None -> -1 sentinel
                    algo        INTEGER NOT NULL DEFAULT -1,   -- None -> -1 sentinel

                    -- payload
                    "datetime"  TIMESTAMPTZ,
                    "value"     DOUBLE PRECISION NOT NULL,

                    PRIMARY KEY ("timestamp", "key", userid, fm, algo)
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
    INSERT INTO withings_measures (userid, "timestamp","key",fm,algo,"datetime","value")
    VALUES %s
    ON CONFLICT ("timestamp","key",fm,algo) DO UPDATE
      SET "datetime" = EXCLUDED."datetime",
          "value"    = EXCLUDED."value";
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
             cur.execute(delete_sql, (userid, startdate, enddate))

             if values:
                extras.execute_values(cur, insert_sql, values, template="(%s,%s,%s,%s,%s,%s,%s)", page_size=1000)

        conn.commit()

def upsert_measures_influx(
    rows: Iterable[Dict[str, Any]],
    userid: str,
    startdate: int,
    enddate: int) -> None:
    """
    InfluxDB 1.8 upsert: DELETE window for userid, then write points.
    Measurement: withings
      tags: userid, key, (optional) segment
      fields: value (float), fm (int), algo (int)
      time: r["timestamp"] (seconds)
    """
    client = get_influx_client("fitness")

    # DELETE: InfluxQL needs RFC3339 times; end is exclusive, so add 1s
    start_rfc = _rfc3339_utc(startdate)
    end_rfc   = _rfc3339_utc(enddate + 1)
    delete_q  = (
        f'DELETE FROM "withings" '
        f'WHERE time >= \'{start_rfc}\' AND time < \'{end_rfc}\' '
        f'AND "userid" = \'{userid}\''
    )
    client.query(delete_q)

    # WRITE: build points (JSON format). Preserve ints for fm/algo.
    points: List[Dict[str, Any]] = []
    for r in rows:
        ts = int(r["timestamp"])
        key = str(r["key"])
        val = float(r["value"])
        fm  = -1 if r.get("fm") is None else int(r["fm"])
        algo = -1 if r.get("algo") is None else int(r["algo"])

        tags = {"userid": userid, "key": key}
        seg = r.get("segment")
        if seg:
            tags["segment"] = str(seg)

        points.append({
            "measurement": "withings",
            "tags": tags,
            "time": ts,  # seconds epoch
            "fields": {
                "value": val,
                "fm": fm,
                "algo": algo,
                # optionally: "tz": str(r.get("timezone")) if you want it as a field
            },
        })

    if points:
        client.write_points(
            points,
            time_precision="s",
            retention_policy=retention_policy,
            batch_size=5000,
        )

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
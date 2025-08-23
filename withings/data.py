from connections import get_connection
from datetime import datetime, timedelta

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
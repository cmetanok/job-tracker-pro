import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "jobs.db"

STATUSES = [
    "В планах",
    "Откликнулся",
    "Собеседование",
    "Тестовое задание",
    "Оффер",
    "Отказ",
]
ACTIVE_STATUSES = ["В планах", "Откликнулся", "Собеседование", "Тестовое задание"]


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                url TEXT,
                status TEXT NOT NULL,
                applied_date TEXT,
                rejection_reason TEXT,
                lessons TEXT,
                notes TEXT,
                is_public INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # миграция: добавить is_public, если БД была создана до этого изменения
        if not _column_exists(conn, "jobs", "is_public"):
            conn.execute("ALTER TABLE jobs ADD COLUMN is_public INTEGER DEFAULT 0")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT NOT NULL,
                value TEXT NOT NULL,
                is_public INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        if not _column_exists(conn, "progress", "is_public"):
            conn.execute("ALTER TABLE progress ADD COLUMN is_public INTEGER DEFAULT 0")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_date TEXT NOT NULL,
                action TEXT NOT NULL,
                job_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# ---------- activity ----------
def log_activity(action: str, job_id: int | None = None):
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO activity (activity_date, action, job_id) VALUES (?, ?, ?)",
            (today, action, job_id),
        )
        conn.commit()


def fetch_activity(days: int = 365):
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT activity_date, action FROM activity WHERE activity_date >= ?",
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def calculate_streak() -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT activity_date FROM activity ORDER BY activity_date"
        ).fetchall()

    if not rows:
        return {"current": 0, "best": 0, "last_active": None}

    dates = [date.fromisoformat(r["activity_date"]) for r in rows]
    dates_set = set(dates)

    today = date.today()
    current = 0
    cursor = today if today in dates_set else today - timedelta(days=1)
    while cursor in dates_set:
        current += 1
        cursor -= timedelta(days=1)

    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    best = max(best, current)

    return {
        "current": current,
        "best": best,
        "last_active": dates[-1].isoformat() if dates else None,
    }


# ---------- jobs ----------
def add_job(company, position, url, status, applied_date,
            rejection_reason, lessons, notes, is_public=False):
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO jobs (company, position, url, status, applied_date,
                              rejection_reason, lessons, notes, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company, position, url, status,
              applied_date.isoformat() if applied_date else None,
              rejection_reason, lessons, notes, int(is_public)))
        job_id = cur.lastrowid
        conn.commit()
    log_activity("add_job", job_id)
    return job_id


def update_job(job_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", values)
        conn.commit()
    log_activity("update_job", job_id)


def delete_job(job_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
    log_activity("delete_job", job_id)


def toggle_job_visibility(job_id: int, is_public: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET is_public = ? WHERE id = ?",
            (int(is_public), job_id),
        )
        conn.commit()
    log_activity("toggle_visibility", job_id)


def fetch_jobs(public_only: bool = False):
    """
    public_only=True → только записи с is_public=1.
    public_only=False → все записи.
    """
    query = "SELECT * FROM jobs"
    if public_only:
        query += " WHERE is_public = 1"
    query += " ORDER BY applied_date DESC, id DESC"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def fetch_job(job_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


# ---------- progress ----------
def upsert_progress(metric, value, is_public=False):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM progress WHERE metric = ?", (metric,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE progress SET value = ?, is_public = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, int(is_public), existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO progress (metric, value, is_public) VALUES (?, ?, ?)",
                (metric, value, int(is_public)),
            )
        conn.commit()
    log_activity("update_progress")


def toggle_progress_visibility(metric: str, is_public: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE progress SET is_public = ? WHERE metric = ?",
            (int(is_public), metric),
        )
        conn.commit()
    log_activity("toggle_progress_visibility")


def fetch_progress(public_only: bool = False):
    query = "SELECT * FROM progress"
    if public_only:
        query += " WHERE is_public = 1"
    query += " ORDER BY metric"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]

def fetch_activity_public(days: int = 365):
    """Активность только по публичным вакансиям — для публичного режима."""
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.activity_date, a.action
            FROM activity a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.activity_date >= ? AND j.is_public = 1
        """, (since,)).fetchall()
    return [dict(r) for r in rows]


def calculate_streak_public() -> dict:
    """Streak по публичным вакансиям — для публичного режима."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT a.activity_date
            FROM activity a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.is_public = 1
            ORDER BY a.activity_date
        """).fetchall()

    if not rows:
        return {"current": 0, "best": 0, "last_active": None}

    dates = [date.fromisoformat(r["activity_date"]) for r in rows]
    dates_set = set(dates)

    today = date.today()
    current = 0
    cursor = today if today in dates_set else today - timedelta(days=1)
    while cursor in dates_set:
        current += 1
        cursor -= timedelta(days=1)

    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    best = max(best, current)

    return {
        "current": current,
        "best": best,
        "last_active": dates[-1].isoformat() if dates else None,
    }
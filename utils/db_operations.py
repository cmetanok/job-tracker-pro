import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

STATUSES = [
    "В планах",
    "Откликнулся",
    "Собеседование",
    "Тестовое задание",
    "Оффер",
    "Отказ",
]
ACTIVE_STATUSES = ["В планах", "Откликнулся", "Собеседование", "Тестовое задание"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ---------- подключение ----------

@st.cache_resource(show_spinner=False)
def _get_client():
    """Клиент gspread. Кэшируется, чтобы не авторизовываться на каждый запрос."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def _get_spreadsheet():
    client = _get_client()
    return client.open(st.secrets["gsheets"]["spreadsheet_name"])


def _sheet(name: str):
    return _get_spreadsheet().worksheet(name)


def init_db():
    """Проверяет, что все нужные листы существуют."""
    try:
        for name in ("jobs", "progress", "activity"):
            _sheet(name)
    except Exception as e:
        st.error(f"Ошибка подключения к Google Sheets: {e}")
        st.stop()


# ---------- утилиты ----------

def _next_id(ws) -> int:
    """Возвращает следующий свободный ID (максимум + 1)."""
    records = ws.get_all_records()
    if not records:
        return 1
    try:
        return max(int(r.get("id", 0)) for r in records) + 1
    except (ValueError, TypeError):
        return len(records) + 1


def _row_number_by_id(ws, job_id) -> int | None:
    """
    Находит номер строки в листе по ID.
    Строка 1 — заголовки, данные начинаются со строки 2.
    Возвращает None, если не найдено.
    """
    records = ws.get_all_records()
    for idx, rec in enumerate(records):
        if str(rec.get("id")) == str(job_id):
            return idx + 2  # +1 за 0-индекс, +1 за строку заголовков
    return None


def _clear_cache():
    """Сбрасывает кэш gspread, чтобы данные подтянулись заново."""
    _get_spreadsheet.clear()


# ---------- activity ----------

def log_activity(action: str, job_id: int | None = None):
    try:
        ws = _sheet("activity")
        new_id = _next_id(ws)
        ws.append_row(
            [new_id, date.today().isoformat(), action, job_id if job_id else ""],
            value_input_option="USER_ENTERED",
        )
    except Exception:
        # Активность — вспомогательная, не ломаем приложение из-за неё
        pass


def fetch_activity(days: int = 365):
    try:
        ws = _sheet("activity")
        records = ws.get_all_records()
    except Exception:
        return []

    since = (date.today() - timedelta(days=days)).isoformat()
    return [
        {"activity_date": r["activity_date"], "action": r["action"]}
        for r in records
        if str(r.get("activity_date", "")) >= since
    ]


def fetch_activity_public(days: int = 365):
    """Активность только по публичным вакансиям."""
    try:
        jobs_ws = _sheet("jobs")
        jobs = jobs_ws.get_all_records()
        public_ids = {
            str(j["id"]) for j in jobs if int(j.get("is_public", 0) or 0) == 1
        }

        ws = _sheet("activity")
        records = ws.get_all_records()
    except Exception:
        return []

    since = (date.today() - timedelta(days=days)).isoformat()
    return [
        {"activity_date": r["activity_date"], "action": r["action"]}
        for r in records
        if str(r.get("activity_date", "")) >= since
        and str(r.get("job_id", "")) in public_ids
    ]


def _calculate_streak_from_dates(dates: list[date]) -> dict:
    if not dates:
        return {"current": 0, "best": 0, "last_active": None}

    dates_set = set(dates)

    today = date.today()
    current = 0
    cursor = today if today in dates_set else today - timedelta(days=1)
    while cursor in dates_set:
        current += 1
        cursor -= timedelta(days=1)

    sorted_dates = sorted(dates)
    best = 1
    run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    best = max(best, current)

    return {
        "current": current,
        "best": best,
        "last_active": sorted_dates[-1].isoformat(),
    }


def calculate_streak() -> dict:
    try:
        ws = _sheet("activity")
        records = ws.get_all_records()
    except Exception:
        return {"current": 0, "best": 0, "last_active": None}

    dates = []
    for r in records:
        val = str(r.get("activity_date", "")).strip()
        if val:
            try:
                dates.append(date.fromisoformat(val))
            except ValueError:
                continue
    return _calculate_streak_from_dates(dates)


def calculate_streak_public() -> dict:
    try:
        jobs_ws = _sheet("jobs")
        jobs = jobs_ws.get_all_records()
        public_ids = {
            str(j["id"]) for j in jobs if int(j.get("is_public", 0) or 0) == 1
        }

        ws = _sheet("activity")
        records = ws.get_all_records()
    except Exception:
        return {"current": 0, "best": 0, "last_active": None}

    dates = []
    for r in records:
        if str(r.get("job_id", "")) not in public_ids:
            continue
        val = str(r.get("activity_date", "")).strip()
        if val:
            try:
                dates.append(date.fromisoformat(val))
            except ValueError:
                continue
    return _calculate_streak_from_dates(dates)


# ---------- jobs ----------

def add_job(company, position, url, status, applied_date,
            rejection_reason, lessons, notes, is_public=False):
    ws = _sheet("jobs")
    new_id = _next_id(ws)
    row = [
        new_id,
        company,
        position,
        url or "",
        status,
        applied_date.isoformat() if applied_date else "",
        rejection_reason or "",
        lessons or "",
        notes or "",
        int(is_public),
        date.today().isoformat(),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    log_activity("add_job", new_id)
    return new_id


def update_job(job_id, **fields):
    if not fields:
        return
    ws = _sheet("jobs")
    headers = ws.row_values(1)
    row_num = _row_number_by_id(ws, job_id)
    if row_num is None:
        return

    # Собираем данные для пакетного обновления
    updates = []
    for key, value in fields.items():
        if key not in headers:
            continue
        col_num = headers.index(key) + 1
        # gspread ожидает A1-нотацию для batch update
        cell = gspread.utils.rowcol_to_a1(row_num, col_num)
        updates.append({"range": cell, "values": [[value]]})

    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")

    log_activity("update_job", job_id)


def delete_job(job_id):
    ws = _sheet("jobs")
    row_num = _row_number_by_id(ws, job_id)
    if row_num is not None:
        ws.delete_rows(row_num)
    log_activity("delete_job", job_id)


def toggle_job_visibility(job_id, is_public):
    ws = _sheet("jobs")
    headers = ws.row_values(1)
    row_num = _row_number_by_id(ws, job_id)
    if row_num is None or "is_public" not in headers:
        return
    col_num = headers.index("is_public") + 1
    ws.update_cell(row_num, col_num, int(is_public))
    log_activity("toggle_visibility", job_id)


def fetch_jobs(public_only: bool = False):
    ws = _sheet("jobs")
    records = ws.get_all_records()

    jobs = []
    for r in records:
        # Нормализуем типы: gspread отдаёт строки и bool'ы вперемешку
        try:
            r["id"] = int(r.get("id", 0))
        except (ValueError, TypeError):
            continue

        try:
            r["is_public"] = int(r.get("is_public", 0) or 0)
        except (ValueError, TypeError):
            r["is_public"] = 0

        r["company"] = str(r.get("company", "")).strip()
        r["position"] = str(r.get("position", "")).strip()
        r["status"] = str(r.get("status", "")).strip()

        if not r["company"] and not r["position"]:
            continue

        jobs.append(r)

    if public_only:
        jobs = [j for j in jobs if j["is_public"] == 1]

    jobs.sort(key=lambda x: str(x.get("applied_date") or ""), reverse=True)
    return jobs


def fetch_job(job_id):
    jobs = fetch_jobs()
    for j in jobs:
        if j["id"] == job_id:
            return j
    return None


# ---------- progress ----------

def upsert_progress(metric, value, is_public=False):
    ws = _sheet("progress")
    headers = ws.row_values(1)
    records = ws.get_all_records()

    row_num = None
    for idx, rec in enumerate(records):
        if str(rec.get("metric", "")).strip() == metric:
            row_num = idx + 2
            break

    if row_num is not None:
        # Обновляем
        updates = []
        if "value" in headers:
            col = headers.index("value") + 1
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_num, col),
                "values": [[value]],
            })
        if "is_public" in headers:
            col = headers.index("is_public") + 1
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_num, col),
                "values": [[int(is_public)]],
            })
        if "updated_at" in headers:
            col = headers.index("updated_at") + 1
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_num, col),
                "values": [[date.today().isoformat()]],
            })
        if updates:
            ws.batch_update(updates, value_input_option="USER_ENTERED")
    else:
        # Вставляем
        new_id = _next_id(ws)
        row = [
            new_id,
            metric,
            value,
            int(is_public),
            date.today().isoformat(),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    log_activity("update_progress")


def toggle_progress_visibility(metric, is_public):
    ws = _sheet("progress")
    headers = ws.row_values(1)
    records = ws.get_all_records()

    if "is_public" not in headers:
        return

    col = headers.index("is_public") + 1
    for idx, rec in enumerate(records):
        if str(rec.get("metric", "")).strip() == metric:
            ws.update_cell(idx + 2, col, int(is_public))
            break
    log_activity("toggle_progress_visibility")


def fetch_progress(public_only: bool = False):
    ws = _sheet("progress")
    records = ws.get_all_records()

    items = []
    for r in records:
        try:
            r["id"] = int(r.get("id", 0))
        except (ValueError, TypeError):
            continue
        try:
            r["is_public"] = int(r.get("is_public", 0) or 0)
        except (ValueError, TypeError):
            r["is_public"] = 0

        metric = str(r.get("metric", "")).strip()
        if not metric:
            continue
        r["metric"] = metric
        items.append(r)

    if public_only:
        items = [i for i in items if i["is_public"] == 1]

    items.sort(key=lambda x: x["metric"])
    return items
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta
from utils.style import apply_global_style
apply_global_style()
from utils.db_operations import (
    init_db, fetch_activity, fetch_activity_public,
    calculate_streak, calculate_streak_public,
)
from utils.privacy import toggle_mode, is_full_access, get_visible_jobs

st.set_page_config(page_title="О проекте", layout="wide")
init_db()

with st.sidebar:
    toggle_mode()

full = is_full_access()

# ============ ИНТРО ============
st.title("Job Tracker Pro")
st.markdown(
    """
    Привет! Это мой трекер поиска работы.

    Я системно подхожу к процессу, хочу фиксировать каждый отклик, анализировать отказы,
    отслеживать прогресс навыков и делиться выводами. Этот проект — не только
    инструмент для меня, но и демонстрация того, как я работаю с данными.
    """
)

if not full:
    st.caption("Публичный режим: показаны только те данные, которые я решил открыть.")

jobs = get_visible_jobs()
total = len(jobs)
offers = sum(1 for j in jobs if j["status"] == "Оффер")
interviews = sum(
    1 for j in jobs
    if j["status"] in ("Собеседование", "Тестовое задание", "Оффер")
)

c1, c2, c3 = st.columns(3)
c1.metric("Откликов", total)
c2.metric("Собеседований", interviews)
c3.metric("Офферов", offers)

st.divider()

# ============ STREAK ============
streak = calculate_streak() if full else calculate_streak_public()

st.subheader("Streak — дни подряд в поиске")
s1, s2, s3 = st.columns(3)
s1.metric("Текущий streak", f"{streak['current']} дн.")
s2.metric("Лучший streak", f"{streak['best']} дн.")
s3.metric("Последняя активность", streak["last_active"] or "—")

if streak["current"] == 0:
    st.caption("Пока нет активности сегодня.")
elif streak["current"] < 3:
    st.caption("Хорошее начало!")
elif streak["current"] < 7:
    st.caption("Уже почти неделя подряд — отличный темп!")
else:
    st.success(f"Ты в поиске уже {streak['current']} дней подряд. Так держать!")

st.divider()

# ============ ТЕПЛОВАЯ КАРТА ============
st.subheader("Активность за последний год")

activity = fetch_activity(days=365) if full else fetch_activity_public(days=365)

if not activity:
    st.caption("Пока нет данных об активности.")
else:
    df = pd.DataFrame(activity)
    df["activity_date"] = pd.to_datetime(df["activity_date"])

    daily = df.groupby(df["activity_date"].dt.date).size().reset_index(name="count")
    daily.columns = ["date", "count"]
    daily["date"] = pd.to_datetime(daily["date"])

    today = date.today()
    start = today - timedelta(days=364)
    start = start - timedelta(days=start.weekday())
    full_range = pd.date_range(start=start, end=today, freq="D")

    grid = pd.DataFrame({"date": full_range})
    grid = grid.merge(daily, on="date", how="left")
    grid["count"] = grid["count"].fillna(0).astype(int)
    grid["week"] = ((grid["date"] - grid["date"].min()).dt.days // 7)
    grid["weekday"] = grid["date"].dt.weekday

    heatmap = (
        alt.Chart(grid)
        .mark_rect(cornerRadius=2, stroke="#ebedf0", strokeWidth=0.5)
        .encode(
            x=alt.X("week:O", title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y(
                "weekday:O",
                title=None,
                sort=[0, 1, 2, 3, 4, 5, 6],
                axis=alt.Axis(
                    labelExpr=(
                        "[0,1,2,3,4,5,6][datum.value] == 0 ? 'Пн' :"
                        " [0,1,2,3,4,5,6][datum.value] == 2 ? 'Ср' :"
                        " [0,1,2,3,4,5,6][datum.value] == 4 ? 'Пт' : ''"
                    ),
                    ticks=False,
                ),
            ),
            color=alt.Color(
                "count:Q",
                scale=alt.Scale(
                    domain=[0, 1, 2, 3, 4, 5],
                    range=["#ebedf0", "#c6e48b", "#7bc96f", "#239a3b", "#196127", "#0e4429"],
                ),
                legend=alt.Legend(title="Активность"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Дата"),
                alt.Tooltip("count:Q", title="Действий"),
            ],
        )
        .properties(height=160)
    )

    st.altair_chart(heatmap, use_container_width=True)

st.divider()

st.subheader("Что внутри")
st.markdown(
    """
    - **Дашборд** - общая аналитика, воронка успешности, динамика откликов.
    - **Добавить вакансию** - форма для новой записи.
    - **Мои вакансии** - таблица с фильтрацией.
    - **Мой прогресс** - уроки из отказов, рост навыков, резюме.
    """
)

from utils.privacy import is_full_access

if is_full_access():
    st.divider()
    st.subheader("Источник данных")
    st.markdown("Данные хранятся в Google Sheets.")
    st.link_button(
        "Открыть Google Таблицу",
        "https://docs.google.com/spreadsheets/d/1JRgp21sp9m22tETNoJY3BZxmaOlBKyZKhyFJYfqZSoY/edit?gid=0#gid=0",
    )

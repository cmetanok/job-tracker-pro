import streamlit as st
import pandas as pd
import altair as alt
from utils.style import apply_global_style
apply_global_style()

from utils.db_operations import init_db
from utils.privacy import (
    toggle_mode, is_full_access, get_visible_jobs
)

st.set_page_config(page_title="Job Tracker Pro", layout="wide")
init_db()

with st.sidebar:
    toggle_mode()

st.title("Job Tracker Pro — Дашборд")

full = is_full_access()
if not full:
    st.caption("Публичный режим: показаны только записи, отмеченные как публичные.")

jobs = get_visible_jobs()

if not jobs:
    st.info("Нет данных для отображения в текущем режиме.")
    st.stop()

df = pd.DataFrame(jobs)
df["applied_date"] = pd.to_datetime(df["applied_date"], errors="coerce")

total = len(df)
active = df["status"].isin(
    ["В планах", "Откликнулся", "Собеседование", "Тестовое задание"]
).sum()
offers = (df["status"] == "Оффер").sum()

c1, c2, c3 = st.columns(3)
c1.metric("Всего откликов", total)
c2.metric("В работе", int(active))
c3.metric("Офферов", int(offers))

st.divider()

st.subheader("Воронка успешности")
funnel_data = pd.DataFrame({
    "Этап": ["Отклики", "Собеседования", "Тестовые", "Офферы"],
    "Кол-во": [
        df["status"].isin(
            ["Откликнулся", "Собеседование", "Тестовое задание", "Оффер", "Отказ"]
        ).sum(),
        df["status"].isin(["Собеседование", "Тестовое задание", "Оффер"]).sum(),
        df["status"].isin(["Тестовое задание", "Оффер"]).sum(),
        (df["status"] == "Оффер").sum(),
    ],
})
st.altair_chart(
    alt.Chart(funnel_data).mark_bar().encode(
        x=alt.X("Этап:N", sort=funnel_data["Этап"].tolist()),
        y="Кол-во:Q",
        color=alt.Color("Этап:N", legend=None),
    ).properties(height=300),
    use_container_width=True,
)

st.subheader("Динамика откликов по дням")
dyn = (
    df.dropna(subset=["applied_date"])
      .groupby(df["applied_date"].dt.date)
      .size()
      .reset_index(name="count")
)
dyn.columns = ["date", "count"]
if not dyn.empty:
    st.altair_chart(
        alt.Chart(dyn).mark_line(point=True).encode(
            x="date:T", y="count:Q", tooltip=["date", "count"]
        ).properties(height=300),
        use_container_width=True,
    )
else:
    st.caption("Нет данных с датами отклика.")

# анализ отказов — только полный доступ
if full:
    st.divider()
    st.subheader("Топ-5 причин отказов")
    rej = df[
        (df["status"] == "Отказ")
        & (df["rejection_reason"].notna())
        & (df["rejection_reason"] != "")
    ]
    if not rej.empty:
        top = rej["rejection_reason"].value_counts().head(5).reset_index()
        top.columns = ["Причина", "Кол-во"]
        st.altair_chart(
            alt.Chart(top).mark_bar().encode(
                x="Кол-во:Q", y=alt.Y("Причина:N", sort="-x")
            ),
            use_container_width=True,
        )
    else:
        st.caption("Причины отказов пока не заполнены.")
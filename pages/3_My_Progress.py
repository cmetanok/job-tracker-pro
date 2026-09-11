import streamlit as st
import pandas as pd
from utils.style import apply_global_style
apply_global_style()

from utils.db_operations import (
    init_db, fetch_jobs, fetch_progress, upsert_progress,
    toggle_progress_visibility
)
from utils.privacy import (
    toggle_mode, is_full_access, mask_company
)

st.set_page_config(page_title="Мой прогресс")
init_db()

with st.sidebar:
    toggle_mode()

st.title("Мой прогресс и выводы")

full = is_full_access()
jobs = fetch_jobs(public_only=not full)

# --- Уроки из отказов ---
st.subheader("Уроки из отказов")
rejections = [
    j for j in jobs
    if j["status"] == "Отказ" and (j["lessons"] or "").strip()
]

if not rejections:
    st.caption("Пока нет заполненных выводов по отказам.")
else:
    rows = []
    for i, j in enumerate(rejections):
        rows.append({
            "Компания": mask_company(j, i),
            "Должность": j["position"],
            "Причина отказа": j["rejection_reason"] or "—",
            "Что я узнал": j["lessons"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# --- Блок прогресса ---
st.subheader("Мой прогресс за время поиска")

progress = fetch_progress(public_only=not full)

if full:
    with st.form("progress_form"):
        metric = st.selectbox("Метрика", [
            "Количество пройденных курсов",
            "Улучшенные навыки",
            "Ссылки на новые пет-проекты",
        ])
        value = st.text_input("Значение (например: SQL: с базового до продвинутого)")
        is_public = st.checkbox("Показывать публично", value=False)
        ok = st.form_submit_button("Сохранить")

    if ok and value.strip():
        upsert_progress(metric, value, is_public=is_public)
        st.success("Сохранено")
        st.rerun()

if progress:
    st.table(pd.DataFrame(progress)[["metric", "value", "updated_at"]])

    if full:
        st.markdown("**Управление видимостью метрик:**")
        for p in progress:
            col1, col2 = st.columns([1, 5])
            with col1:
                new_state = st.checkbox(
                    "Публично",
                    value=bool(p["is_public"]),
                    key=f"prog_vis_{p['metric']}",
                    label_visibility="collapsed",
                )
            with col2:
                st.write(f"**{p['metric']}**: {p['value']}")
            if new_state != bool(p["is_public"]):
                toggle_progress_visibility(p["metric"], new_state)
                st.rerun()
else:
    st.caption("Данные о прогрессе пока не заполнены.")

st.divider()

# --- Резюме ---
st.subheader("Резюме")

total = len(jobs)
interviews = sum(
    1 for j in jobs
    if j["status"] in ("Собеседование", "Тестовое задание", "Оффер")
)
reasons = [
    j["rejection_reason"] for j in jobs
    if j["status"] == "Отказ" and j["rejection_reason"]
]
top_reason = pd.Series(reasons).mode().iloc[0] if reasons else "—"

st.info(
    f"За время поиска я откликнулся на **{total}** вакансий, "
    f"прошел **{interviews}** собеседований. "
    f"Основная причина отказов: **{top_reason}**. "
    f"Я поработал над этим и чувствую себя увереннее."
)
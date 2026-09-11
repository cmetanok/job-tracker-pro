import streamlit as st
import pandas as pd
from datetime import date
from utils.style import apply_global_style
apply_global_style()

from utils.db_operations import (
    init_db, fetch_jobs, update_job, delete_job, toggle_job_visibility, STATUSES
)
from utils.privacy import (
    toggle_mode, is_full_access, mask_company, mask_url, mask_notes
)

st.set_page_config(page_title="Мои вакансии")
init_db()

with st.sidebar:
    toggle_mode()

st.title("Мои вакансии")

full = is_full_access()

# в публичном режиме — только публичные записи
jobs = fetch_jobs(public_only=not full)

show_completed = st.checkbox("Показать завершенные (Отказ / Оффер)")
if not show_completed:
    jobs = [j for j in jobs if j["status"] not in ("Отказ", "Оффер")]

if not jobs:
    st.info("Нет записей по текущему фильтру.")
    if not full:
        st.caption("В публичном режиме показываются только записи с флагом «Показывать публично».")
    st.stop()

# --- таблица ---
rows = []
for i, j in enumerate(jobs):
    rows.append({
        "ID": j["id"],
        "Публично": "✅" if j["is_public"] else "❌",
        "Компания": mask_company(j, i),
        "Должность": j["position"],
        "Статус": j["status"],
        "Дата": j["applied_date"] or "—",
        "Ссылка": mask_url(j["url"]),
        "Выводы": j["lessons"] or "—",
        "Заметки": mask_notes(j["notes"]),
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

if not full:
    st.info(
        "Ты в публичном режиме. Видны только отмеченные записи, "
        "компании и ссылки замаскированы. Для полного доступа переключи режим в сайдбаре."
    )
    st.stop()

# ============================================================
# Ниже — только для полного доступа
# ============================================================
st.divider()

# --- управление видимостью ---
st.subheader(" Управление видимостью")
st.caption("Отметь записи, которые должны быть видны в публичном режиме.")

for j in jobs:
    col1, col2, col3 = st.columns([1, 4, 2])
    with col1:
        new_state = st.checkbox(
            "Публично",
            value=bool(j["is_public"]),
            key=f"vis_{j['id']}",
            label_visibility="collapsed",
        )
    with col2:
        st.write(f"**{j['company']}** — {j['position']}  \n_{j['status']}_")
    with col3:
        if new_state != bool(j["is_public"]):
            toggle_job_visibility(j["id"], new_state)
            st.rerun()

st.divider()

# --- редактирование ---
st.subheader("Редактировать запись")
ids = [j["id"] for j in jobs]
sel_id = st.selectbox("Выбери ID записи", ids)
job = next(j for j in jobs if j["id"] == sel_id)

with st.form("edit_job"):
    company = st.text_input("Компания", value=job["company"])
    position = st.text_input("Должность", value=job["position"])
    url = st.text_input("Ссылка", value=job["url"] or "")
    status = st.selectbox(
        "Статус", STATUSES,
        index=STATUSES.index(job["status"]) if job["status"] in STATUSES else 0
    )
    applied = st.date_input(
        "Дата отклика",
        value=date.fromisoformat(job["applied_date"]) if job["applied_date"] else date.today()
    )
    rejection_reason = st.text_area("Причина отказа", value=job["rejection_reason"] or "")
    lessons = st.text_area("Что я узнал", value=job["lessons"] or "")
    notes = st.text_area("Заметки", value=job["notes"] or "")
    is_public = st.checkbox("Показывать публично", value=bool(job["is_public"]))

    save = st.form_submit_button("Сохранить изменения")

if save:
    if status == "Отказ" and not rejection_reason.strip():
        st.error("При статусе «Отказ» укажи причину.")
    else:
        update_job(
            sel_id,
            company=company, position=position, url=url, status=status,
            applied_date=applied.isoformat(),
            rejection_reason=rejection_reason, lessons=lessons, notes=notes,
            is_public=int(is_public),
        )
        st.success("Обновлено")
        st.rerun()

with st.expander("Удалить запись"):
    del_id = st.selectbox("ID для удаления", ids, key="del_id")
    if st.button("Удалить", type="primary"):
        delete_job(del_id)
        st.success("Удалено")
        st.rerun()
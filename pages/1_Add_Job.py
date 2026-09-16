import streamlit as st
from datetime import date

from utils.db_operations import init_db, add_job, STATUSES
from utils.privacy import toggle_mode, is_full_access

st.set_page_config(page_title="Добавить вакансию", layout="wide")
init_db()

with st.sidebar:
    toggle_mode()

st.title("Добавить вакансию")

if not is_full_access():
    st.info(
        "Добавление вакансий доступно только в полном доступе. "
        "Переключи режим в боковой панели и введи пароль."
    )
    st.stop()

with st.form("add_job"):
    company = st.text_input("Компания *")
    position = st.text_input("Должность *")
    url = st.text_input("Ссылка на вакансию")
    status = st.selectbox("Статус", STATUSES)
    applied_date = st.date_input("Дата отклика", value=date.today())

    rejection_reason = ""
    if status == "Отказ":
        rejection_reason = st.text_area("Причина отказа *")

    lessons = st.text_area("Что я узнал / выводы")
    notes = st.text_area("Заметки")

    is_public = st.checkbox(
        "Показывать публично",
        value=False,
        help="Если включено — запись видна в публичном режиме.",
    )

    submitted = st.form_submit_button("Сохранить")

if submitted:
    errors = []
    if not company.strip():
        errors.append("Укажи компанию.")
    if not position.strip():
        errors.append("Укажи должность.")
    if status == "Отказ" and not rejection_reason.strip():
        errors.append("При статусе «Отказ» нужно указать причину.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        add_job(company, position, url, status, applied_date,
                rejection_reason, lessons, notes, is_public=is_public)
        st.success("Вакансия добавлена.")
        if is_public:
            st.caption("Запись будет видна в публичном режиме.")
        else:
            st.caption("Запись скрыта от публичного режима.")
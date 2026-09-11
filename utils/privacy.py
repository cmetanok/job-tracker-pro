import streamlit as st


def is_public_mode() -> bool:
    return st.session_state.get("public_mode", True)


def is_full_access() -> bool:
    """True, если пользователь в полном доступе (не публичный режим и пароль верный)."""
    return (not is_public_mode()) and st.session_state.get("authed", False)


def toggle_mode():
    st.sidebar.markdown("### 🔒 Режим просмотра")

    public = st.sidebar.toggle(
        "Публичный режим",
        value=st.session_state.get("public_mode", True),
        key="public_mode_toggle",
    )
    st.session_state["public_mode"] = public

    if not public:
        pwd = st.sidebar.text_input(
            "Пароль полного доступа", type="password", key="full_pwd"
        )
        if pwd:
            try:
                expected = st.secrets["auth"]["full_access_password"]
            except Exception:
                st.sidebar.error("Пароль не настроен в secrets.toml")
                st.session_state["public_mode"] = True
                return
            if pwd == expected:
                st.session_state["authed"] = True
                st.sidebar.success("Полный доступ ✅")
            else:
                st.session_state["authed"] = False
                st.sidebar.error("Неверный пароль")
    else:
        st.session_state["authed"] = False


def get_visible_jobs():
    """
    Возвращает список вакансий, которые нужно показать в текущем режиме.
    - Полный доступ: все записи.
    - Публичный режим: только is_public = 1.
    """
    from utils.db_operations import fetch_jobs
    return fetch_jobs(public_only=not is_full_access())


def get_visible_progress():
    from utils.db_operations import fetch_progress
    return fetch_progress(public_only=not is_full_access())


# ---- маскировка полей (для публичного режима) ----
def mask_company(job: dict, idx: int) -> str:
    if is_full_access():
        return job["company"]
    return f"Компания {idx + 1}"


def mask_url(url):
    if not is_full_access() or not url:
        return "—"
    return url


def mask_notes(text):
    if not text:
        return "—"
    return text if is_full_access() else "—"
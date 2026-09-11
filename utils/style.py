import streamlit as st


def apply_global_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:wght@500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #1a1a1a;
        }

        /* Заголовки */
        h1, h2, h3, h4 {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #0f172a;
        }
        h1 { font-size: 2.25rem; margin-bottom: 0.5rem; }
        h2 { font-size: 1.5rem; margin-top: 2rem; }
        h3 { font-size: 1.15rem; }

        /* Убираем дефолтный верхний отступ */
        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            max-width: 1100px;
        }

        /* Кнопки */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            color: #1a1a1a;
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            border-color: #2563eb;
            color: #2563eb;
            background: #f8fafc;
        }
        .stButton > button[kind="primary"] {
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
        }
        .stButton > button[kind="primary"]:hover {
            background: #1d4ed8;
        }

        /* Метрики */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #6b7280;
            font-weight: 500;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.75rem;
            font-weight: 600;
            color: #0f172a;
        }

        /* Таблицы */
        [data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            overflow: hidden;
        }

        /* Сайдбар */
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1.5rem;
        }

        /* Разделители */
        hr {
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 2rem 0;
        }

        /* Инфо-блоки */
        [data-testid="stAlert"] {
            border-radius: 10px;
            border: 1px solid #e5e7eb;
        }

        /* Ссылки */
        a { color: #2563eb; text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* Скрыть футер Streamlit */
        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )
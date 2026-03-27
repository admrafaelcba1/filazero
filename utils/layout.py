import html
import pandas as pd
import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
            :root {
                --fz-primary: #0b3b60;
                --fz-primary-2: #14558a;
                --fz-primary-3: #1f7ac0;
                --fz-bg: #f3f6fb;
                --fz-surface: #ffffff;
                --fz-surface-soft: #f9fbfd;
                --fz-border: #d9e4ef;
                --fz-border-strong: #c3d4e6;
                --fz-text: #142133;
                --fz-text-soft: #314559;
                --fz-muted: #65758a;
                --fz-success: #1d7f49;
                --fz-success-bg: #edf8f1;
                --fz-warning: #9a6700;
                --fz-warning-bg: #fff6e6;
                --fz-danger: #b42318;
                --fz-danger-bg: #fff0f0;
                --fz-info: #175cd3;
                --fz-info-bg: #eef4ff;
                --fz-shadow-xs: 0 2px 8px rgba(15, 23, 42, 0.04);
                --fz-shadow-sm: 0 8px 20px rgba(15, 23, 42, 0.05);
                --fz-shadow-md: 0 14px 32px rgba(15, 23, 42, 0.08);
                --fz-shadow-lg: 0 20px 44px rgba(11, 59, 96, 0.16);
                --fz-radius-xl: 24px;
                --fz-radius-lg: 18px;
                --fz-radius-md: 14px;
                --fz-radius-sm: 12px;
            }

            html, body, [class*="css"] {
                font-family: "Inter", "Segoe UI", sans-serif;
            }

            html, body, .stApp {
                background:
                    radial-gradient(circle at top right, rgba(31,122,192,0.08), transparent 24%),
                    linear-gradient(180deg, #f7f9fc 0%, #eef4f9 100%);
            }

            [data-testid="stHeader"] {
                background: transparent !important;
                height: 0 !important;
            }

            [data-testid="stToolbar"] {
                top: 0.35rem !important;
                right: 0.75rem !important;
            }

            [data-testid="stDecoration"] {
                display: none !important;
            }

            .stApp > header {
                background: transparent !important;
            }

            [data-testid="stAppViewContainer"] > .main {
                background: transparent !important;
            }

            [data-testid="stSidebarNav"] {
                display: none !important;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #08253c 0%, #0d3554 58%, #11476f 100%);
                border-right: 1px solid rgba(255,255,255,0.08);
            }

            [data-testid="stSidebar"] * {
                color: #ffffff;
            }

            [data-testid="stSidebar"] .stRadio label {
                color: #ffffff !important;
                font-weight: 700;
            }

            [data-testid="stSidebar"] .stCaption {
                color: rgba(255,255,255,0.82) !important;
            }

            [data-testid="stSidebar"] .stMarkdown p {
                color: #ffffff;
            }

            [data-testid="stSidebar"] .stRadio > div {
                gap: 0.28rem;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
                padding: 0.48rem 0.68rem 0.48rem 0.55rem;
                transition: all 0.2s ease;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
                background: rgba(255,255,255,0.10);
                border-color: rgba(255,255,255,0.18);
                transform: translateX(2px);
            }

            .block-container {
                padding-top: 0.15rem !important;
                padding-bottom: 1.2rem;
                max-width: 1540px;
            }

            .fz-app-hero {
                background: linear-gradient(135deg, #0b3b60 0%, #14558a 58%, #1f7ac0 100%);
                border-radius: 28px;
                padding: 1.9rem 2rem;
                color: white;
                box-shadow: var(--fz-shadow-lg);
                margin-top: 0 !important;
                margin-bottom: 1.15rem;
                border: 1px solid rgba(255,255,255,0.12);
                position: relative;
                overflow: hidden;
            }

            .fz-app-hero::before {
                content: "";
                position: absolute;
                width: 360px;
                height: 360px;
                border-radius: 50%;
                background: rgba(255,255,255,0.08);
                top: -170px;
                right: -120px;
            }

            .fz-app-hero::after {
                content: "";
                position: absolute;
                width: 180px;
                height: 180px;
                border-radius: 50%;
                background: rgba(255,255,255,0.05);
                bottom: -70px;
                right: 120px;
            }

            .fz-app-kicker {
                position: relative;
                z-index: 2;
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                font-size: 0.78rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                opacity: 0.92;
                font-weight: 800;
                margin-bottom: 0.5rem;
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 999px;
                padding: 0.36rem 0.72rem;
            }

            .fz-app-title {
                position: relative;
                z-index: 2;
                font-size: 2.15rem;
                line-height: 1.08;
                font-weight: 800;
                margin: 0;
            }

            .fz-app-subtitle {
                position: relative;
                z-index: 2;
                margin-top: 0.6rem;
                font-size: 1rem;
                line-height: 1.58;
                opacity: 0.96;
                max-width: 980px;
            }

            .fz-page-header {
                background: rgba(255,255,255,0.88);
                backdrop-filter: blur(8px);
                border: 1px solid var(--fz-border);
                border-radius: var(--fz-radius-xl);
                padding: 1.2rem 1.3rem;
                box-shadow: var(--fz-shadow-sm);
                margin-bottom: 1rem;
            }

            .fz-page-title-wrap {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
                flex-wrap: wrap;
            }

            .fz-page-title {
                margin: 0;
                color: var(--fz-text);
                font-size: 1.58rem;
                font-weight: 800;
                line-height: 1.16;
            }

            .fz-page-desc {
                margin-top: 0.4rem;
                color: var(--fz-muted);
                font-size: 0.98rem;
                line-height: 1.56;
                max-width: 980px;
            }

            .fz-page-tag {
                background: linear-gradient(180deg, #eef6fd 0%, #e2f0fd 100%);
                color: var(--fz-primary);
                border: 1px solid #cfe3f7;
                border-radius: 999px;
                padding: 0.42rem 0.82rem;
                font-size: 0.8rem;
                font-weight: 800;
                white-space: nowrap;
                box-shadow: var(--fz-shadow-xs);
            }

            .fz-section {
                background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(251,253,255,0.98) 100%);
                border: 1px solid var(--fz-border);
                border-radius: var(--fz-radius-xl);
                padding: 1rem 1rem 0.52rem 1rem;
                box-shadow: var(--fz-shadow-sm);
                margin-bottom: 1rem;
                position: relative;
                overflow: hidden;
            }

            .fz-section::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: linear-gradient(90deg, var(--fz-primary) 0%, var(--fz-primary-3) 100%);
                opacity: 0.9;
            }

            .fz-section-title {
                color: var(--fz-text);
                font-size: 1.08rem;
                font-weight: 800;
                margin-bottom: 0.22rem;
            }

            .fz-section-desc {
                color: var(--fz-muted);
                font-size: 0.94rem;
                margin-bottom: 0.85rem;
                line-height: 1.52;
            }

            .fz-info-strip {
                background: linear-gradient(90deg, rgba(20,85,138,0.08) 0%, rgba(31,122,192,0.12) 100%);
                border: 1px solid rgba(20,85,138,0.12);
                border-radius: 16px;
                padding: 0.95rem 1rem;
                margin-bottom: 1rem;
                color: var(--fz-text);
                box-shadow: var(--fz-shadow-sm);
                line-height: 1.55;
            }

            .fz-sidebar-brand {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 18px;
                padding: 1rem 1rem 0.95rem 1rem;
                margin-bottom: 1rem;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
            }

            .fz-sidebar-brand-title {
                font-size: 1.08rem;
                font-weight: 800;
                margin: 0;
                color: #ffffff;
            }

            .fz-sidebar-brand-subtitle {
                margin-top: 0.38rem;
                font-size: 0.89rem;
                line-height: 1.45;
                color: rgba(255,255,255,0.84);
            }

            .fz-sidebar-badge {
                display: inline-block;
                margin-top: 0.75rem;
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 999px;
                padding: 0.26rem 0.62rem;
                font-size: 0.74rem;
                font-weight: 700;
                color: #ffffff;
            }

            .fz-kpi-card {
                background: linear-gradient(180deg, rgba(255,255,255,0.99) 0%, rgba(247,251,255,1) 100%);
                border: 1px solid var(--fz-border);
                border-radius: 20px;
                padding: 1rem 1rem 0.95rem 1rem;
                box-shadow: var(--fz-shadow-sm);
                margin-bottom: 1rem;
                min-height: 132px;
                position: relative;
                overflow: hidden;
            }

            .fz-kpi-card::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
                background: linear-gradient(90deg, var(--fz-primary) 0%, var(--fz-primary-3) 100%);
            }

            .fz-kpi-label {
                color: var(--fz-muted);
                font-size: 0.8rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.42rem;
            }

            .fz-kpi-value {
                color: var(--fz-text);
                font-size: 1.7rem;
                font-weight: 800;
                line-height: 1.08;
                letter-spacing: -0.02em;
            }

            .fz-kpi-help {
                color: var(--fz-muted);
                font-size: 0.86rem;
                margin-top: 0.42rem;
                line-height: 1.44;
            }

            .fz-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                border-radius: 999px;
                padding: 0.34rem 0.74rem;
                font-size: 0.79rem;
                font-weight: 800;
                border: 1px solid transparent;
                white-space: nowrap;
                box-shadow: var(--fz-shadow-xs);
            }

            .fz-badge-neutral {
                background: #f3f6fa;
                color: #425466;
                border-color: #d7e0ea;
            }

            .fz-badge-info {
                background: var(--fz-info-bg);
                color: var(--fz-info);
                border-color: #cfe0ff;
            }

            .fz-badge-success {
                background: var(--fz-success-bg);
                color: var(--fz-success);
                border-color: #cbe9d6;
            }

            .fz-badge-warning {
                background: var(--fz-warning-bg);
                color: var(--fz-warning);
                border-color: #f2ddb1;
            }

            .fz-badge-danger {
                background: var(--fz-danger-bg);
                color: var(--fz-danger);
                border-color: #f3c6c6;
            }

            .fz-progress-card {
                background: linear-gradient(180deg, rgba(255,255,255,0.99) 0%, rgba(247,251,255,1) 100%);
                border: 1px solid var(--fz-border);
                border-radius: 18px;
                padding: 1rem 1rem 0.95rem 1rem;
                box-shadow: var(--fz-shadow-sm);
                margin-bottom: 1rem;
            }

            .fz-progress-top {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 0.8rem;
                margin-bottom: 0.5rem;
            }

            .fz-progress-label {
                color: var(--fz-text);
                font-weight: 800;
                font-size: 0.95rem;
            }

            .fz-progress-value {
                color: var(--fz-primary);
                font-weight: 800;
                font-size: 0.95rem;
            }

            .fz-progress-track {
                width: 100%;
                height: 12px;
                background: #eaf1f8;
                border-radius: 999px;
                overflow: hidden;
                border: 1px solid #dbe6f2;
            }

            .fz-progress-fill {
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, var(--fz-primary) 0%, var(--fz-primary-3) 100%);
            }

            .fz-progress-help {
                margin-top: 0.55rem;
                color: var(--fz-muted);
                font-size: 0.84rem;
                line-height: 1.42;
            }

            .fz-footer {
                margin-top: 1.2rem;
                background: rgba(255,255,255,0.7);
                border: 1px solid var(--fz-border);
                border-radius: 16px;
                padding: 0.85rem 1rem;
                color: var(--fz-muted);
                font-size: 0.86rem;
                line-height: 1.5;
                text-align: center;
                box-shadow: var(--fz-shadow-xs);
            }

            .fz-shell-tagline {
                color: rgba(255,255,255,0.82);
                font-size: 0.82rem;
                line-height: 1.4;
                margin-top: 0.45rem;
            }

            .fz-shell-chip {
                display: inline-block;
                margin-top: 0.55rem;
                margin-right: 0.35rem;
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 999px;
                padding: 0.24rem 0.55rem;
                font-size: 0.72rem;
                font-weight: 700;
                color: #ffffff;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.42rem;
                padding-bottom: 0.25rem;
            }

            .stTabs [data-baseweb="tab"] {
                background: rgba(255,255,255,0.94);
                border-radius: 14px 14px 0 0;
                border: 1px solid var(--fz-border);
                padding-left: 1rem;
                padding-right: 1rem;
                font-weight: 800;
                min-height: 42px;
            }

            .stTabs [aria-selected="true"] {
                color: var(--fz-primary) !important;
                border-color: #bfd4e8 !important;
                background: #ffffff !important;
                box-shadow: var(--fz-shadow-xs);
            }

            .stTextInput label,
            .stNumberInput label,
            .stTextArea label,
            .stSelectbox label,
            .stMultiSelect label,
            .stDateInput label,
            .stTimeInput label,
            div[data-testid="stWidgetLabel"] p,
            div[data-testid="stWidgetLabel"] label {
                font-weight: 800 !important;
                color: var(--fz-text) !important;
                letter-spacing: 0.01em;
            }

            .stTextInput > div > div > input,
            .stNumberInput input,
            .stTextArea textarea,
            .stSelectbox div[data-baseweb="select"] > div,
            .stMultiSelect div[data-baseweb="select"] > div,
            .stDateInput input,
            .stTimeInput input {
                border-radius: 14px !important;
                border: 1px solid var(--fz-border-strong) !important;
                background: #ffffff !important;
                min-height: 48px;
            }

            .stTextArea textarea {
                min-height: 128px !important;
            }

            .stForm {
                background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(249,252,255,0.99) 100%);
                border: 1px solid var(--fz-border);
                border-radius: 20px;
                padding: 1.1rem 1.1rem 0.95rem 1.1rem;
                box-shadow: var(--fz-shadow-sm);
                overflow: visible !important;
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 14px !important;
                font-weight: 800 !important;
                min-height: 2.85rem;
            }

            .stFormSubmitButton > button {
                border-radius: 14px !important;
                border: none !important;
                background: linear-gradient(135deg, var(--fz-primary) 0%, var(--fz-primary-3) 100%) !important;
                color: #ffffff !important;
                font-weight: 800 !important;
                min-height: 3rem;
                box-shadow: 0 10px 24px rgba(11, 59, 96, 0.20) !important;
                white-space: normal !important;
                line-height: 1.2 !important;
                padding: 0.7rem 1rem !important;
            }

            .stAlert {
                border-radius: 16px !important;
                border: 1px solid var(--fz-border) !important;
                box-shadow: var(--fz-shadow-sm);
            }

            div[data-testid="stDataFrame"] {
                border: 1px solid var(--fz-border) !important;
                border-radius: 18px !important;
                overflow: hidden !important;
                box-shadow: var(--fz-shadow-sm) !important;
                background: #ffffff !important;
            }

            div[data-testid="stDataFrame"] [role="columnheader"] {
                background: linear-gradient(180deg, #eef5fb 0%, #e4eef9 100%) !important;
                color: var(--fz-primary) !important;
                font-weight: 800 !important;
                border-bottom: 1px solid var(--fz-border) !important;
            }

            .fz-table-wrap {
                background: #ffffff;
                border: 1px solid var(--fz-border);
                border-radius: 18px;
                box-shadow: var(--fz-shadow-sm);
                overflow: auto;
                width: 100%;
            }

            .fz-table {
                width: 100%;
                min-width: 1100px;
                border-collapse: separate;
                border-spacing: 0;
                font-size: 0.94rem;
            }

            .fz-table thead th {
                position: sticky;
                top: 0;
                z-index: 2;
                background: linear-gradient(180deg, #eef5fb 0%, #e4eef9 100%);
                color: var(--fz-primary);
                text-align: left;
                font-weight: 800;
                padding: 0.85rem 0.8rem;
                border-bottom: 1px solid var(--fz-border);
                border-right: 1px solid #e8eef5;
                white-space: nowrap;
            }

            .fz-table tbody td {
                padding: 0.78rem 0.8rem;
                border-bottom: 1px solid #e8eef5;
                border-right: 1px solid #eef3f8;
                color: var(--fz-text-soft);
                white-space: nowrap;
                background: #ffffff;
            }

            .fz-table tbody tr:nth-child(even) td {
                background: #fbfdff;
            }

            .fz-table tbody tr:hover td {
                background: #f3f8fe;
            }

            .fz-table th:last-child,
            .fz-table td:last-child {
                border-right: none;
            }

            hr {
                border: none;
                border-top: 1px solid var(--fz-border);
                margin: 1.1rem 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    st.markdown(
        """
        <div class="fz-sidebar-brand">
            <div class="fz-sidebar-brand-title">Fila Zero na Cirurgia</div>
            <div class="fz-sidebar-brand-subtitle">
                Ambiente administrativo modular para acompanhamento operacional,
                financeiro e gerencial do programa.
            </div>
            <div class="fz-sidebar-badge">Base modular ativa</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_context():
    st.markdown(
        """
        <div class="fz-shell-tagline">
            Sistema orientado à gestão de propostas, execução, pagamento e remanejamento
            com foco em controle operacional e segurança do fluxo.
        </div>
        <div class="fz-shell-chip">SES/MT</div>
        <div class="fz-shell-chip">Governança</div>
        <div class="fz-shell-chip">Ambiente institucional</div>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(titulo: str, subtitulo: str):
    titulo = html.escape(titulo)
    subtitulo = html.escape(subtitulo)

    st.markdown(
        f"""
        <div class="fz-app-hero">
            <div class="fz-app-kicker">Secretaria de Estado de Saúde de Mato Grosso</div>
            <div class="fz-app-title">{titulo}</div>
            <div class="fz-app-subtitle">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
        <div class="fz-footer">
            Sistema Fila Zero na Cirurgia • Ambiente administrativo modular para gestão institucional,
            acompanhamento operacional e consolidação gerencial do programa.
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(titulo: str, descricao: str | None = None, tag: str | None = None):
    titulo = html.escape(titulo)
    descricao_html = f'<div class="fz-page-desc">{html.escape(descricao)}</div>' if descricao else ""
    tag_html = f'<div class="fz-page-tag">{html.escape(tag)}</div>' if tag else ""

    st.markdown(
        f"""
        <div class="fz-page-header">
            <div class="fz-page-title-wrap">
                <div>
                    <div class="fz-page-title">{titulo}</div>
                    {descricao_html}
                </div>
                {tag_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(titulo: str, descricao: str | None = None):
    titulo = html.escape(titulo)
    descricao_html = f'<div class="fz-section-desc">{html.escape(descricao)}</div>' if descricao else ""

    st.markdown(
        f"""
        <div class="fz-section">
            <div class="fz-section-title">{titulo}</div>
            {descricao_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_strip(texto: str):
    st.markdown(
        f"""
        <div class="fz-info-strip">
            {html.escape(texto)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(texto: str, variant: str = "neutral"):
    texto = html.escape(texto)
    variant = variant if variant in {"neutral", "info", "success", "warning", "danger"} else "neutral"

    st.markdown(
        f"""
        <div class="fz-badge fz-badge-{variant}">
            {texto}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, valor: str, ajuda: str | None = None):
    label = html.escape(label)
    valor = html.escape(valor)
    ajuda_html = f'<div class="fz-kpi-help">{html.escape(ajuda)}</div>' if ajuda else ""

    st.markdown(
        f"""
        <div class="fz-kpi-card">
            <div class="fz-kpi-label">{label}</div>
            <div class="fz-kpi-value">{valor}</div>
            {ajuda_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def progress_card(label: str, percentual: float, ajuda: str | None = None):
    percentual = max(0.0, min(float(percentual or 0), 100.0))
    ajuda_html = f'<div class="fz-progress-help">{html.escape(ajuda)}</div>' if ajuda else ""

    st.markdown(
        f"""
        <div class="fz-progress-card">
            <div class="fz-progress-top">
                <div class="fz-progress-label">{html.escape(label)}</div>
                <div class="fz-progress-value">{percentual:.2f}%</div>
            </div>
            <div class="fz-progress-track">
                <div class="fz-progress-fill" style="width:{percentual:.2f}%"></div>
            </div>
            {ajuda_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_variant_from_text(status: str | None) -> str:
    if not status:
        return "neutral"

    s = status.strip().lower()

    if any(x in s for x in ["pago", "concluído", "concluido", "finalizado", "aprovado integral"]):
        return "success"
    if any(x in s for x in ["parcial", "pendente", "atenção", "atencao"]):
        return "warning"
    if any(x in s for x in ["erro", "bloque", "reprov", "cancel"]):
        return "danger"
    if any(x in s for x in ["execução", "execucao", "análise", "analise", "tramitação", "tramitacao"]):
        return "info"

    return "neutral"


def render_html_table(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("Nenhum registro encontrado.")
        return

    html_table = df.to_html(index=False, escape=False, classes="fz-table")
    st.markdown(
        f"""
        <div class="fz-table-wrap">
            {html_table}
        </div>
        """,
        unsafe_allow_html=True,
    )
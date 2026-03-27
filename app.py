from pathlib import Path
import importlib.util

import streamlit as st

from database import criar_tabelas
from services.importacao_service import importar_catalogo_automaticamente_se_existir
from utils.layout import (
    inject_global_css,
    render_app_header,
    render_footer,
    render_sidebar_brand,
    render_sidebar_context,
)

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Sistema Fila Zero SES/MT",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

criar_tabelas()
importar_catalogo_automaticamente_se_existir()
inject_global_css()

PAGINAS = {
    "Painel Executivo": "pages/dashboard.py",
    "Cadastros Básicos": "pages/cadastros.py",
    "Catálogo de Procedimentos": "pages/catalogo.py",
    "Propostas e Autorização": "pages/propostas.py",
    "Execução": "pages/execucao.py",
    "Pagamentos": "pages/pagamentos.py",
    "Remanejamento Financeiro": "pages/remanejamento.py",
}


def carregar_modulo(caminho_relativo: str):
    arquivo = BASE_DIR / caminho_relativo

    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo da página não encontrado: {arquivo}")

    nome_modulo = arquivo.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(nome_modulo, arquivo)

    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar o módulo: {arquivo}")

    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


with st.sidebar:
    render_sidebar_brand()
    render_sidebar_context()

    pagina_escolhida = st.radio(
        "Módulos do Sistema",
        list(PAGINAS.keys()),
        label_visibility="visible",
    )

    st.markdown("---")
    st.caption("Versão modular focada em separação entre interface e regras de negócio.")
    st.caption("Ambiente visual refinado para operação institucional.")

render_app_header(
    titulo="Sistema Fila Zero na Cirurgia",
    subtitulo=(
        "Base modular para gestão de propostas, catálogo, execução, "
        "pagamentos e remanejamentos financeiros."
    ),
)

try:
    modulo = carregar_modulo(PAGINAS[pagina_escolhida])

    if hasattr(modulo, "render"):
        modulo.render()
    else:
        st.error(
            f"O arquivo '{PAGINAS[pagina_escolhida]}' precisa ter uma função chamada render()."
        )
except Exception as e:
    st.error("Ocorreu um erro ao carregar o módulo selecionado.")
    st.exception(e)

render_footer()
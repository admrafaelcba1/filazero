import pandas as pd
import streamlit as st

from database import get_connection
from services.catalogo_service import (
    excluir_procedimento,
    inserir_ou_atualizar_procedimento,
    listar_procedimentos,
    obter_procedimento_por_id,
)
from services.executor_service import (
    UF_OPCOES,
    inserir_ou_atualizar_executor,
    listar_executores,
)
from services.proponente_service import (
    inserir_ou_atualizar_proponente,
    listar_proponentes,
)
from utils.layout import (
    info_strip,
    page_header,
    render_html_table,
    section_header,
)


def _formatar_moeda(valor) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _texto(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def excluir_proponente(proponente_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        uso = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM propostas
            WHERE proponente_id = ?
            """,
            (proponente_id,),
        ).fetchone()

        if int(uso["total"] or 0) > 0:
            conn.execute(
                """
                UPDATE proponentes
                SET status = 'Inativo', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (proponente_id,),
            )
            conn.commit()
            return True, "Proponente desativado com sucesso, pois já possui uso em propostas."

        conn.execute("DELETE FROM proponentes WHERE id = ?", (proponente_id,))
        conn.commit()
        return True, "Proponente excluído com sucesso."
    finally:
        conn.close()


def excluir_executor(executor_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        uso_h = conn.execute(
            "SELECT COUNT(*) AS total FROM execucao_hospitalar WHERE executor_id = ?",
            (executor_id,),
        ).fetchone()
        uso_a = conn.execute(
            "SELECT COUNT(*) AS total FROM execucao_ambulatorial WHERE executor_id = ?",
            (executor_id,),
        ).fetchone()
        uso_p = conn.execute(
            "SELECT COUNT(*) AS total FROM pagamentos WHERE executor_id = ?",
            (executor_id,),
        ).fetchone()

        total_uso = int(uso_h["total"] or 0) + int(uso_a["total"] or 0) + int(uso_p["total"] or 0)

        if total_uso > 0:
            conn.execute(
                """
                UPDATE executores
                SET status = 'Inativo', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (executor_id,),
            )
            conn.commit()
            return True, "Executor desativado com sucesso, pois já possui uso operacional."

        conn.execute("DELETE FROM executores WHERE id = ?", (executor_id,))
        conn.commit()
        return True, "Executor excluído com sucesso."
    finally:
        conn.close()


def render():
    page_header(
        "Cadastros básicos",
        "Gestão dos registros estruturantes do sistema, com foco em procedimentos, proponentes e executores.",
        tag="Base administrativa",
    )

    info_strip(
        "Mantenha esta base atualizada para garantir integridade no cadastro de propostas, "
        "na execução e nos pagamentos do programa."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Procedimentos",
            "Proponentes",
            "Executores",
        ]
    )

    with tab1:
        section_header(
            "Cadastro manual de procedimentos",
            "Consulta, inserção, edição e exclusão de procedimentos da base operacional.",
        )

        filtro_proc = st.text_input(
            "Pesquisar procedimento por código, descrição, classificação interna ou subgrupo",
            key="filtro_proc_cadastros",
        )

        df_proc = listar_procedimentos(filtro=filtro_proc)

        if df_proc.empty:
            st.info("Nenhum procedimento encontrado.")
        else:
            df_proc_exibir = df_proc.copy()
            df_proc_exibir["valor_unitario"] = df_proc_exibir["valor_unitario"].apply(_formatar_moeda)

            render_html_table(
                df_proc_exibir[
                    [
                        "id",
                        "codigo_sigtap",
                        "descricao_procedimento",
                        "valor_unitario",
                        "complexidade",
                        "numeracao",
                        "registro",
                        "classificacao_interna",
                        "subgrupo_cod",
                        "subgrupo_descricao",
                        "classificacao",
                        "natureza",
                        "ativo",
                    ]
                ].rename(
                    columns={
                        "id": "ID",
                        "codigo_sigtap": "CÓDIGO SIGTAP",
                        "descricao_procedimento": "DESCRIÇÃO DO PROCEDIMENTO",
                        "valor_unitario": "VALOR UNITÁRIO",
                        "complexidade": "COMPLEXIDADE",
                        "numeracao": "NUMERAÇÃO",
                        "registro": "REGISTRO",
                        "classificacao_interna": "CLASSIFICAÇÃO INTERNA",
                        "subgrupo_cod": "SUB-GRUPO-COD",
                        "subgrupo_descricao": "SUB-GRUPO-DESCRIÇÃO",
                        "classificacao": "CLASSIFICAÇÃO",
                        "natureza": "NATUREZA",
                        "ativo": "ATIVO",
                    }
                )
            )

        section_header(
            "Inserir ou editar procedimento",
            "Selecione um registro para edição ou deixe em branco para cadastrar um novo procedimento.",
        )

        procedimento_id = None
        procedimento = None

        if not df_proc.empty:
            opcoes_proc = {
                f"{row['id']} | {row['codigo_sigtap']} | {row['descricao_procedimento']}": int(row["id"])
                for _, row in df_proc.iterrows()
            }

            selecionado = st.selectbox(
                "Selecionar procedimento para edição",
                options=[None] + list(opcoes_proc.keys()),
                format_func=lambda x: "Novo procedimento" if x is None else x,
                key="proc_edicao_select",
            )

            if selecionado is not None:
                procedimento_id = opcoes_proc[selecionado]
                procedimento = obter_procedimento_por_id(procedimento_id)

        with st.form("form_procedimento"):
            c1, c2, c3 = st.columns(3)
            codigo_sigtap = c1.text_input(
                "CÓDIGO SIGTAP",
                value=_texto(procedimento["codigo_sigtap"]) if procedimento else "",
            )
            valor_unitario = c2.number_input(
                "VALOR UNITÁRIO",
                min_value=0.0,
                value=float(procedimento["valor_unitario"]) if procedimento else 0.0,
                step=0.01,
                format="%.2f",
            )
            classificacao = c3.selectbox(
                "CLASSIFICAÇÃO",
                options=["", "AMB", "HOSP", "AMB/HOSP"],
                index=(
                    ["", "AMB", "HOSP", "AMB/HOSP"].index(_texto(procedimento["classificacao"]).upper())
                    if procedimento and _texto(procedimento["classificacao"]).upper() in ["", "AMB", "HOSP", "AMB/HOSP"]
                    else 0
                ),
            )

            descricao_procedimento = st.text_area(
                "DESCRIÇÃO DO PROCEDIMENTO",
                value=_texto(procedimento["descricao_procedimento"]) if procedimento else "",
            )

            d1, d2, d3, d4 = st.columns(4)
            complexidade = d1.text_input("COMPLEXIDADE", value=_texto(procedimento["complexidade"]) if procedimento else "")
            numeracao = d2.text_input("NUMERAÇÃO", value=_texto(procedimento["numeracao"]) if procedimento else "")
            registro = d3.text_input("REGISTRO", value=_texto(procedimento["registro"]) if procedimento else "")
            classificacao_interna = d4.text_input(
                "CLASSIFICAÇÃO INTERNA",
                value=_texto(procedimento["classificacao_interna"]) if procedimento else "",
            )

            e1, e2, e3 = st.columns(3)
            subgrupo_cod = e1.text_input("SUB-GRUPO-COD", value=_texto(procedimento["subgrupo_cod"]) if procedimento else "")
            subgrupo_descricao = e2.text_input(
                "SUB-GRUPO-DESCRIÇÃO",
                value=_texto(procedimento["subgrupo_descricao"]) if procedimento else "",
            )
            natureza = e3.text_input("NATUREZA", value=_texto(procedimento["natureza"]) if procedimento else "")

            f1, f2 = st.columns(2)
            origem = f1.text_input("ORIGEM", value=_texto(procedimento["origem"]) if procedimento else "MANUAL")
            ativo = f2.selectbox(
                "ATIVO",
                options=[1, 0],
                index=0 if not procedimento or int(procedimento["ativo"] or 1) == 1 else 1,
                format_func=lambda x: "Sim" if x == 1 else "Não",
            )

            g1, g2 = st.columns(2)
            salvar_proc = g1.form_submit_button("Salvar procedimento", use_container_width=True)
            excluir_proc = g2.form_submit_button(
                "Excluir procedimento",
                use_container_width=True,
                disabled=procedimento_id is None,
            )

            if salvar_proc:
                ok, msg = inserir_ou_atualizar_procedimento(
                    {
                        "id": procedimento_id,
                        "codigo_sigtap": codigo_sigtap,
                        "descricao_procedimento": descricao_procedimento,
                        "valor_unitario": valor_unitario,
                        "complexidade": complexidade,
                        "numeracao": numeracao,
                        "registro": registro,
                        "classificacao_interna": classificacao_interna,
                        "subgrupo_cod": subgrupo_cod,
                        "subgrupo_descricao": subgrupo_descricao,
                        "classificacao": classificacao,
                        "natureza": natureza,
                        "origem": origem,
                        "ativo": ativo,
                    }
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            if excluir_proc and procedimento_id is not None:
                ok, msg = excluir_procedimento(procedimento_id)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab2:
        section_header(
            "Cadastro de proponentes",
            "Cadastro e manutenção dos proponentes que poderão registrar propostas no sistema.",
        )

        filtro_prop = st.text_input("Pesquisar proponente", key="filtro_prop_cadastros")
        df_prop = listar_proponentes(filtro=filtro_prop)

        with st.form("form_proponente", clear_on_submit=False):
            selecionado_prop = None
            proponente_edicao = None

            if not df_prop.empty:
                opcoes_prop = {
                    f"{row['id']} | {row['proponente']}": int(row["id"])
                    for _, row in df_prop.iterrows()
                }
                selecionado_prop = st.selectbox(
                    "Selecionar proponente para edição",
                    options=[None] + list(opcoes_prop.keys()),
                    format_func=lambda x: "Novo proponente" if x is None else x,
                )
                if selecionado_prop is not None:
                    proponente_id = opcoes_prop[selecionado_prop]
                    linha = df_prop[df_prop["id"] == proponente_id]
                    if not linha.empty:
                        proponente_edicao = linha.iloc[0]

            a1, a2, a3 = st.columns(3)
            proponente = a1.text_input(
                "PROPONENTE",
                value=_texto(proponente_edicao["proponente"]) if proponente_edicao is not None else "",
            )
            ibge = a2.text_input(
                "IBGE",
                value=_texto(proponente_edicao["ibge"]) if proponente_edicao is not None else "",
            )
            cnes = a3.text_input(
                "CNES",
                value=_texto(proponente_edicao["cnes"]) if proponente_edicao is not None else "",
            )

            b1, b2, b3 = st.columns(3)
            cnpj_fms = b1.text_input(
                "CNPJ FMS",
                value=_texto(proponente_edicao["cnpj_fms"]) if proponente_edicao is not None else "",
            )
            nome_completo = b2.text_input(
                "NOME COMPLETO",
                value=_texto(proponente_edicao["nome_completo"]) if proponente_edicao is not None else "",
            )
            status = b3.selectbox(
                "STATUS",
                options=["Ativo", "Inativo"],
                index=0 if proponente_edicao is None or _texto(proponente_edicao["status"]) != "Inativo" else 1,
            )

            c1, c2 = st.columns(2)
            salvar_prop = c1.form_submit_button("Salvar proponente", use_container_width=True)
            excluir_prop = c2.form_submit_button(
                "Excluir proponente",
                use_container_width=True,
                disabled=proponente_edicao is None,
            )

            if salvar_prop:
                ok, msg = inserir_ou_atualizar_proponente(
                    {
                        "proponente": proponente,
                        "ibge": ibge,
                        "cnes": cnes,
                        "cnpj_fms": cnpj_fms,
                        "nome_completo": nome_completo,
                        "status": status,
                    }
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            if excluir_prop and proponente_edicao is not None:
                ok, msg = excluir_proponente(int(proponente_edicao["id"]))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        if df_prop.empty:
            st.info("Nenhum proponente cadastrado.")
        else:
            render_html_table(
                df_prop.rename(
                    columns={
                        "id": "ID",
                        "proponente": "PROPONENTE",
                        "ibge": "IBGE",
                        "cnes": "CNES",
                        "cnpj_fms": "CNPJ FMS",
                        "nome_completo": "NOME COMPLETO",
                        "status": "STATUS",
                    }
                )
            )

    with tab3:
        section_header(
            "Cadastro de executores",
            "Cadastro e manutenção dos estabelecimentos executores utilizados nas etapas operacionais.",
        )

        filtro_exec = st.text_input("Pesquisar executor", key="filtro_exec_cadastros")
        df_exec = listar_executores(filtro=filtro_exec)

        with st.form("form_executor", clear_on_submit=False):
            selecionado_exec = None
            executor_edicao = None

            if not df_exec.empty:
                opcoes_exec = {
                    f"{row['id']} | {row['cnes']} | {row['estabelecimento']}": int(row["id"])
                    for _, row in df_exec.iterrows()
                }
                selecionado_exec = st.selectbox(
                    "Selecionar executor para edição",
                    options=[None] + list(opcoes_exec.keys()),
                    format_func=lambda x: "Novo executor" if x is None else x,
                )
                if selecionado_exec is not None:
                    executor_id = opcoes_exec[selecionado_exec]
                    linha = df_exec[df_exec["id"] == executor_id]
                    if not linha.empty:
                        executor_edicao = linha.iloc[0]

            d1, d2 = st.columns(2)
            cnes = d1.text_input(
                "CNES",
                value=_texto(executor_edicao["cnes"]) if executor_edicao is not None else "",
            )
            estabelecimento = d2.text_input(
                "ESTABELECIMENTO",
                value=_texto(executor_edicao["estabelecimento"]) if executor_edicao is not None else "",
            )

            e1, e2, e3, e4 = st.columns(4)
            ibge = e1.text_input(
                "IBGE",
                value=_texto(executor_edicao["ibge"]) if executor_edicao is not None else "",
            )
            municipio = e2.text_input(
                "MUNICÍPIO",
                value=_texto(executor_edicao["municipio"]) if executor_edicao is not None else "",
            )
            estado_padrao = _texto(executor_edicao["estado"]) if executor_edicao is not None else "MT"
            estado = e3.selectbox(
                "ESTADO",
                options=[""] + UF_OPCOES,
                index=([""] + UF_OPCOES).index(estado_padrao) if estado_padrao in ([""] + UF_OPCOES) else 0,
            )
            status = e4.selectbox(
                "STATUS",
                options=["Ativo", "Inativo"],
                index=0 if executor_edicao is None or _texto(executor_edicao["status"]) != "Inativo" else 1,
            )

            f1, f2 = st.columns(2)
            salvar_exec = f1.form_submit_button("Salvar executor", use_container_width=True)
            excluir_exec = f2.form_submit_button(
                "Excluir executor",
                use_container_width=True,
                disabled=executor_edicao is None,
            )

            if salvar_exec:
                ok, msg = inserir_ou_atualizar_executor(
                    {
                        "cnes": cnes,
                        "estabelecimento": estabelecimento,
                        "ibge": ibge,
                        "municipio": municipio,
                        "estado": estado,
                        "status": status,
                    }
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

            if excluir_exec and executor_edicao is not None:
                ok, msg = excluir_executor(int(executor_edicao["id"]))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        if df_exec.empty:
            st.info("Nenhum executor cadastrado.")
        else:
            render_html_table(
                df_exec.rename(
                    columns={
                        "id": "ID",
                        "cnes": "CNES",
                        "estabelecimento": "ESTABELECIMENTO",
                        "ibge": "IBGE",
                        "municipio": "MUNICÍPIO",
                        "estado": "ESTADO",
                        "status": "STATUS",
                    }
                )
            )
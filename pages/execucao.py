import streamlit as st

from services.alerta_service import listar_alertas_proposta_df
from services.execucao_service import (
    TIPOS_EXECUCAO,
    listar_execucoes_proposta,
    listar_executores,
    listar_itens_autorizados_com_saldo,
    listar_propostas_para_execucao,
    obter_resumo_proposta_execucao,
    registrar_execucao,
)
from services.exportacao_service import exportar_execucao_excel
from services.fase_service import obter_contexto_fase_proposta
from utils.layout import (
    info_strip,
    kpi_card,
    page_header,
    render_html_table,
    section_header,
    status_badge,
)

MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _formatar_moeda(valor) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render():
    page_header(
        "Execução",
        "Lançamento da execução hospitalar e ambulatorial com trava por fase da proposta e por saldo autorizado do item.",
        tag="Fase operacional",
    )

    info_strip(
        "Aqui a equipe registra as execuções efetivamente realizadas. O sistema respeita a fase da proposta "
        "e impede lançamentos acima do quantitativo autorizado."
    )

    df_prop = listar_propostas_para_execucao()
    if df_prop.empty:
        st.info("Nenhuma proposta cadastrada para execução.")
        return

    section_header(
        "Pesquisa e seleção da proposta",
        "Filtre a proposta desejada, selecione o registro e exporte a base de execução, se necessário.",
    )

    f1, f2, f3 = st.columns([2, 1, 1])
    filtro_proponente = f1.selectbox(
        "Filtrar por proponente",
        options=[None] + sorted(df_prop["proponente_exibicao"].dropna().unique().tolist()),
        format_func=lambda x: "Todos" if x is None else x,
    )
    filtro_status = f2.selectbox(
        "Filtrar por status",
        options=[None] + sorted(df_prop["status"].dropna().unique().tolist()),
        format_func=lambda x: "Todos" if x is None else x,
    )

    if filtro_proponente:
        df_prop = df_prop[df_prop["proponente_exibicao"] == filtro_proponente]
    if filtro_status:
        df_prop = df_prop[df_prop["status"] == filtro_status]

    if df_prop.empty:
        st.info("Nenhuma proposta encontrada com os filtros informados.")
        return

    opcoes = {
        f"{row['numero_proposta']} | {row['proponente_exibicao']} | {MESES.get(int(row['competencia_mes']), '-')}/{int(row['competencia_ano'])}": int(row["id"])
        for _, row in df_prop.iterrows()
    }

    proposta_label = f3.selectbox("Selecione a proposta", list(opcoes.keys()))
    proposta_id = opcoes[proposta_label]

    excel = exportar_execucao_excel(proposta_id=proposta_id)
    st.download_button(
        "Exportar execução da proposta",
        data=excel,
        file_name=f"execucao_proposta_{proposta_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    proposta = obter_resumo_proposta_execucao(proposta_id)
    itens = listar_itens_autorizados_com_saldo(proposta_id)
    executores = listar_executores()
    contexto = obter_contexto_fase_proposta(proposta_id)
    alertas_df = listar_alertas_proposta_df(proposta_id)

    section_header(
        "Resumo da proposta selecionada",
        "Quadro sintético da proposta atualmente em análise na tela de execução.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Número", str(proposta["numero_proposta"]))
    with c2:
        kpi_card("Status", str(proposta["status"] or "-"))
    with c3:
        kpi_card("Valor Total", _formatar_moeda(proposta["valor_total"]))
    with c4:
        kpi_card("Valor Aprovado", _formatar_moeda(proposta["valor_aprovado"]))

    st.markdown(
        f"""
        **Proponente:** {proposta.get('proponente_exibicao') or '-'}  
        **Competência:** {MESES.get(int(proposta['competencia_mes'] or 0), '-')} / {proposta.get('competencia_ano') or '-'}
        """
    )

    if contexto["pode_executar"]:
        status_badge("Execução liberada para esta proposta", "success")
    else:
        status_badge(contexto["mensagem_execucao"], "warning")

    if not alertas_df.empty:
        status_badge(f"Esta proposta possui {len(alertas_df)} alerta(s) operacional(is)", "warning")

    section_header(
        "Itens autorizados e saldo disponível",
        "Tabela operacional com o saldo ainda disponível para lançamento de execução em cada item.",
    )

    if itens.empty:
        st.warning("Esta proposta não possui itens.")
        return

    itens_exibir = itens.copy()
    itens_exibir["valor_unitario"] = itens_exibir["valor_unitario"].apply(_formatar_moeda)
    itens_exibir["valor_total"] = itens_exibir["valor_total"].apply(_formatar_moeda)
    itens_exibir["valor_autorizado"] = itens_exibir["valor_autorizado"].apply(_formatar_moeda)
    itens_exibir["saldo_valor"] = itens_exibir["saldo_valor"].apply(_formatar_moeda)

    render_html_table(
        itens_exibir[
            [
                "id",
                "codigo_procedimento",
                "descricao_procedimento",
                "classificacao",
                "natureza",
                "quantidade",
                "quantidade_autorizada",
                "qtd_executada_hospitalar",
                "qtd_executada_ambulatorial",
                "qtd_executada_total",
                "saldo_quantidade",
                "valor_unitario",
                "valor_autorizado",
                "saldo_valor",
            ]
        ].rename(
            columns={
                "id": "ID",
                "codigo_procedimento": "CÓDIGO",
                "descricao_procedimento": "DESCRIÇÃO",
                "classificacao": "CLASSIFICAÇÃO",
                "natureza": "NATUREZA",
                "quantidade": "QTD. PROPOSTA",
                "quantidade_autorizada": "QTD. AUTORIZADA",
                "qtd_executada_hospitalar": "EXEC. HOSP",
                "qtd_executada_ambulatorial": "EXEC. AMB",
                "qtd_executada_total": "EXEC. TOTAL",
                "saldo_quantidade": "SALDO QTD.",
                "valor_unitario": "VALOR UNITÁRIO",
                "valor_autorizado": "VALOR AUTORIZADO",
                "saldo_valor": "SALDO VALOR",
            }
        )
    )

    itens_com_saldo = itens[itens["saldo_quantidade"] > 0].copy()

    section_header(
        "Registrar execução",
        "Preencha o formulário abaixo para lançar a produção executada por item e executor.",
    )

    if not contexto["pode_executar"]:
        st.info("O formulário de execução está bloqueado para esta proposta.")
    elif executores.empty:
        st.warning("Não há executores cadastrados. Cadastre ao menos um CNES Executor antes de registrar execução.")
    elif itens_com_saldo.empty:
        st.info("Todos os itens desta proposta já foram executados no limite autorizado.")
    else:
        item_map = {
            f"{row['id']} | {row['codigo_procedimento']} | saldo: {int(row['saldo_quantidade'])}": int(row["id"])
            for _, row in itens_com_saldo.iterrows()
        }

        mapa_executor = {
            f"{row['cnes']} - {row['estabelecimento']} ({row['municipio']})": (int(row["id"]), row["cnes"])
            for _, row in executores.iterrows()
        }

        with st.form("form_execucao"):
            a1, a2, a3, a4 = st.columns(4)
            item_label = a1.selectbox("Item da proposta", list(item_map.keys()))
            tipo_execucao = a2.selectbox("Tipo de execução", TIPOS_EXECUCAO)
            competencia_mes = a3.selectbox("Competência - mês", list(MESES.keys()), format_func=lambda x: MESES[x])
            competencia_ano = a4.number_input("Competência - ano", min_value=2024, max_value=2100, value=2026, step=1)

            executor_label = st.selectbox("CNES Executor", list(mapa_executor.keys()))
            executor_id, cnes_executor = mapa_executor[executor_label]

            item_id = item_map[item_label]
            item_row = itens_com_saldo[itens_com_saldo["id"] == item_id].iloc[0]

            b1, b2, b3, b4 = st.columns(4)
            b1.text_input("Código", value=str(item_row["codigo_procedimento"]), disabled=True)
            b2.text_input("Natureza", value=str(item_row["natureza"] or ""), disabled=True)
            b3.number_input("Qtd. autorizada", value=int(item_row["quantidade_autorizada"] or 0), disabled=True)
            b4.number_input("Saldo disponível", value=int(item_row["saldo_quantidade"] or 0), disabled=True)

            st.text_input("Descrição", value=str(item_row["descricao_procedimento"]), disabled=True)

            c1, c2 = st.columns(2)
            quantidade = c1.number_input(
                "Quantidade executada",
                min_value=1,
                max_value=int(item_row["saldo_quantidade"]),
                value=1,
                step=1,
            )
            valor_previsto = int(quantidade) * float(item_row["valor_unitario"] or 0)
            c2.number_input("Valor da execução", value=valor_previsto, disabled=True)

            observacao = st.text_area("Observação")
            submitted = st.form_submit_button("Registrar execução", use_container_width=True)

            if submitted:
                ok, msg = registrar_execucao(
                    proposta_id=proposta_id,
                    item_proposta_id=item_id,
                    tipo_execucao=tipo_execucao,
                    competencia_mes=int(competencia_mes),
                    competencia_ano=int(competencia_ano),
                    quantidade=int(quantidade),
                    executor_id=executor_id,
                    cnes_executor=cnes_executor,
                    observacao=observacao,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    section_header(
        "Histórico de execuções",
        "Relação das execuções já registradas para a proposta selecionada.",
    )

    historico = listar_execucoes_proposta(proposta_id)
    if historico.empty:
        st.info("Nenhuma execução registrada para esta proposta.")
    else:
        historico_exibir = historico.copy()
        historico_exibir["competencia"] = (
            historico_exibir["competencia_mes"].map(MESES) + "/" + historico_exibir["competencia_ano"].astype(str)
        )
        historico_exibir["valor_total"] = historico_exibir["valor_total"].apply(_formatar_moeda)

        render_html_table(
            historico_exibir[
                [
                    "id",
                    "tipo_execucao",
                    "competencia",
                    "cnes_executor",
                    "executor_estabelecimento",
                    "codigo_procedimento",
                    "descricao_procedimento",
                    "quantidade",
                    "valor_total",
                    "observacao",
                    "created_at",
                ]
            ].rename(
                columns={
                    "id": "ID",
                    "tipo_execucao": "TIPO",
                    "competencia": "COMPETÊNCIA",
                    "cnes_executor": "CNES",
                    "executor_estabelecimento": "EXECUTOR",
                    "codigo_procedimento": "CÓDIGO",
                    "descricao_procedimento": "DESCRIÇÃO",
                    "quantidade": "QUANTIDADE",
                    "valor_total": "VALOR TOTAL",
                    "observacao": "OBSERVAÇÃO",
                    "created_at": "CRIADO EM",
                }
            )
        )
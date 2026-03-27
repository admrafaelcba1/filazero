import streamlit as st

from services.alerta_service import listar_alertas_proposta_df
from services.execucao_service import listar_executores
from services.exportacao_service import exportar_pagamentos_excel
from services.fase_service import obter_contexto_fase_proposta
from services.pagamento_service import (
    TIPOS_PAGAMENTO,
    listar_itens_com_saldo_pagamento,
    listar_pagamentos_proposta,
    listar_propostas_para_pagamento,
    obter_resumo_proposta_pagamento,
    registrar_pagamento,
)
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
        "Pagamentos",
        "Registro dos pagamentos por proposta, item e tipo de execução, respeitando o saldo já executado e ainda não pago.",
        tag="Fase financeira",
    )

    info_strip(
        "Esta tela controla o desembolso operacional da proposta. O sistema só permite pagamento dentro do saldo "
        "executado e compatível com o tipo de execução informado."
    )

    df_prop = listar_propostas_para_pagamento()
    if df_prop.empty:
        st.info("Nenhuma proposta cadastrada para pagamento.")
        return

    section_header(
        "Pesquisa e seleção da proposta",
        "Filtre a proposta desejada e exporte a base de pagamentos, se necessário.",
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

    excel = exportar_pagamentos_excel(proposta_id=proposta_id)
    st.download_button(
        "Exportar pagamentos da proposta",
        data=excel,
        file_name=f"pagamentos_proposta_{proposta_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    proposta = obter_resumo_proposta_pagamento(proposta_id)
    itens = listar_itens_com_saldo_pagamento(proposta_id)
    executores = listar_executores()
    contexto = obter_contexto_fase_proposta(proposta_id)
    alertas_df = listar_alertas_proposta_df(proposta_id)

    section_header(
        "Resumo da proposta selecionada",
        "Quadro sintético da proposta no contexto da fase de pagamento.",
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

    if contexto["pode_pagar"]:
        status_badge("Pagamento liberado para esta proposta", "success")
    else:
        status_badge(contexto["mensagem_pagamento"], "warning")

    if not alertas_df.empty:
        status_badge(f"Esta proposta possui {len(alertas_df)} alerta(s) operacional(is)", "warning")

    section_header(
        "Itens com saldo para pagamento",
        "Tabela detalhada dos valores executados, já pagos e ainda disponíveis para pagamento por item.",
    )

    if itens.empty:
        st.warning("Esta proposta não possui itens.")
        return

    itens_exibir = itens.copy()
    for col in [
        "valor_unitario",
        "valor_total",
        "valor_autorizado",
        "valor_exec_hospitalar",
        "valor_exec_ambulatorial",
        "valor_exec_total",
        "valor_pago_hospitalar",
        "valor_pago_ambulatorial",
        "valor_pago_total",
        "saldo_pag_hospitalar",
        "saldo_pag_ambulatorial",
        "saldo_pagamento_total",
    ]:
        itens_exibir[col] = itens_exibir[col].apply(_formatar_moeda)

    render_html_table(
        itens_exibir[
            [
                "id",
                "codigo_procedimento",
                "descricao_procedimento",
                "natureza",
                "valor_unitario",
                "qtd_exec_hospitalar",
                "qtd_exec_ambulatorial",
                "valor_exec_hospitalar",
                "valor_exec_ambulatorial",
                "valor_pago_hospitalar",
                "valor_pago_ambulatorial",
                "saldo_pag_hospitalar",
                "saldo_pag_ambulatorial",
                "saldo_pagamento_total",
            ]
        ].rename(
            columns={
                "id": "ID",
                "codigo_procedimento": "CÓDIGO",
                "descricao_procedimento": "DESCRIÇÃO",
                "natureza": "NATUREZA",
                "valor_unitario": "VALOR UNITÁRIO",
                "qtd_exec_hospitalar": "QTD. EXEC. HOSP",
                "qtd_exec_ambulatorial": "QTD. EXEC. AMB",
                "valor_exec_hospitalar": "VALOR EXEC. HOSP",
                "valor_exec_ambulatorial": "VALOR EXEC. AMB",
                "valor_pago_hospitalar": "VALOR PAGO HOSP",
                "valor_pago_ambulatorial": "VALOR PAGO AMB",
                "saldo_pag_hospitalar": "SALDO HOSP",
                "saldo_pag_ambulatorial": "SALDO AMB",
                "saldo_pagamento_total": "SALDO TOTAL",
            }
        )
    )

    section_header(
        "Registrar pagamento",
        "Informe o item, o tipo de pagamento e o valor a pagar, respeitando o saldo disponível do tipo selecionado.",
    )

    itens_com_saldo = itens[(itens["saldo_pag_hospitalar"] > 0) | (itens["saldo_pag_ambulatorial"] > 0)].copy()

    if not contexto["pode_pagar"]:
        st.info("O formulário de pagamento está bloqueado para esta proposta.")
    elif executores.empty:
        st.warning("Não há executores cadastrados. Cadastre ao menos um CNES Executor antes de registrar pagamento.")
    elif itens_com_saldo.empty:
        st.info("Não há saldo de pagamento disponível para esta proposta.")
    else:
        item_map = {
            f"{row['id']} | {row['codigo_procedimento']} | {row['descricao_procedimento']}": int(row["id"])
            for _, row in itens_com_saldo.iterrows()
        }

        mapa_executor = {
            f"{row['cnes']} - {row['estabelecimento']} ({row['municipio']})": (int(row["id"]), row["cnes"])
            for _, row in executores.iterrows()
        }

        with st.form("form_pagamento"):
            a1, a2 = st.columns(2)
            item_label = a1.selectbox("Item da proposta", list(item_map.keys()))
            tipo_execucao = a2.selectbox("Tipo de pagamento", TIPOS_PAGAMENTO)

            executor_label = st.selectbox("CNES Executor", list(mapa_executor.keys()))
            executor_id, cnes_executor = mapa_executor[executor_label]

            item_id = item_map[item_label]
            item_row = itens_com_saldo[itens_com_saldo["id"] == item_id].iloc[0]

            if tipo_execucao == "HOSPITALAR":
                saldo_tipo = float(item_row["saldo_pag_hospitalar"] or 0)
                valor_executado_tipo = float(item_row["valor_exec_hospitalar"] or 0)
                valor_pago_tipo = float(item_row["valor_pago_hospitalar"] or 0)
            else:
                saldo_tipo = float(item_row["saldo_pag_ambulatorial"] or 0)
                valor_executado_tipo = float(item_row["valor_exec_ambulatorial"] or 0)
                valor_pago_tipo = float(item_row["valor_pago_ambulatorial"] or 0)

            b1, b2, b3 = st.columns(3)
            b1.number_input("Valor executado no tipo", value=valor_executado_tipo, disabled=True)
            b2.number_input("Valor já pago no tipo", value=valor_pago_tipo, disabled=True)
            b3.number_input("Saldo disponível", value=saldo_tipo, disabled=True)

            valor_pago = st.number_input(
                "Valor a pagar",
                min_value=0.01,
                max_value=max(0.01, saldo_tipo) if saldo_tipo > 0 else 0.01,
                value=0.01 if saldo_tipo <= 0 else min(0.01, saldo_tipo),
                step=0.01,
                format="%.2f",
            )

            observacao = st.text_area("Observação")
            submitted = st.form_submit_button("Registrar pagamento", use_container_width=True)

            if submitted:
                ok, msg = registrar_pagamento(
                    proposta_id=proposta_id,
                    item_proposta_id=item_id,
                    tipo_execucao=tipo_execucao,
                    valor_pago=float(valor_pago),
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
        "Histórico de pagamentos",
        "Relação dos pagamentos já registrados para a proposta selecionada.",
    )

    historico = listar_pagamentos_proposta(proposta_id)
    if historico.empty:
        st.info("Nenhum pagamento registrado para esta proposta.")
    else:
        historico_exibir = historico.copy()
        historico_exibir["valor_pago"] = historico_exibir["valor_pago"].apply(_formatar_moeda)

        render_html_table(
            historico_exibir[
                [
                    "id",
                    "tipo_execucao",
                    "cnes_executor",
                    "executor_estabelecimento",
                    "codigo_procedimento",
                    "descricao_procedimento",
                    "valor_pago",
                    "observacao",
                    "created_at",
                ]
            ].rename(
                columns={
                    "id": "ID",
                    "tipo_execucao": "TIPO",
                    "cnes_executor": "CNES",
                    "executor_estabelecimento": "EXECUTOR",
                    "codigo_procedimento": "CÓDIGO",
                    "descricao_procedimento": "DESCRIÇÃO",
                    "valor_pago": "VALOR PAGO",
                    "observacao": "OBSERVAÇÃO",
                    "created_at": "CRIADO EM",
                }
            )
        )
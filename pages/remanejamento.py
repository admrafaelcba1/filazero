import streamlit as st

from services.exportacao_service import exportar_remanejamentos_excel
from services.remanejamento_service import (
    efetivar_remanejamento,
    listar_historico_remanejamentos,
    listar_itens_para_remanejamento,
    listar_propostas_para_remanejamento,
    obter_resumo_geral_remanejamentos,
    obter_resumo_proposta_remanejamento,
    simular_remanejamento,
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
        "Remanejamento financeiro",
        "Redistribuição controlada de quantitativos e valores entre itens da mesma proposta, respeitando travas operacionais.",
        tag="Ajuste interno",
    )

    info_strip(
        "Utilize esta tela para remanejar saldo entre itens da mesma proposta sem ultrapassar os limites "
        "já autorizados e sem comprometer o que já foi executado."
    )

    resumo_geral = obter_resumo_geral_remanejamentos()

    section_header(
        "Resumo geral de remanejamentos",
        "Indicadores consolidados das movimentações registradas no sistema.",
    )

    a1, a2, a3 = st.columns(3)
    with a1:
        kpi_card("Total de remanejamentos", str(resumo_geral["total_remanejamentos"]))
    with a2:
        kpi_card("Valor remanejado", _formatar_moeda(resumo_geral["total_valor_remanejado"]))
    with a3:
        kpi_card("Saldo residual", _formatar_moeda(resumo_geral["total_saldo_residual"]))

    df_prop = listar_propostas_para_remanejamento()
    if df_prop.empty:
        st.info("Nenhuma proposta disponível para remanejamento.")
        return

    section_header(
        "Pesquisa e seleção da proposta",
        "Escolha a proposta que será utilizada na operação de remanejamento.",
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

    excel = exportar_remanejamentos_excel(proposta_id=proposta_id)
    st.download_button(
        "Exportar remanejamentos",
        data=excel,
        file_name=f"remanejamentos_proposta_{proposta_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    resumo_prop = obter_resumo_proposta_remanejamento(proposta_id)
    itens = listar_itens_para_remanejamento(proposta_id)

    section_header(
        "Resumo da proposta selecionada",
        "Quadro sintético da proposta atualmente em análise para remanejamento.",
    )

    if resumo_prop:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            kpi_card("Número", str(resumo_prop.get("numero_proposta") or "-"))
        with b2:
            kpi_card("Status", str(resumo_prop.get("status") or "-"))
        with b3:
            kpi_card("Valor Total", _formatar_moeda(resumo_prop.get("valor_total") or 0))
        with b4:
            kpi_card("Valor Aprovado", _formatar_moeda(resumo_prop.get("valor_aprovado") or 0))

        st.markdown(
            f"""
            **Proponente:** {resumo_prop.get('proponente_exibicao') or '-'}  
            **Competência:** {MESES.get(int(resumo_prop.get('competencia_mes') or 0), '-')} / {resumo_prop.get('competencia_ano') or '-'}
            """
        )

    section_header(
        "Itens da proposta e saldos remanejáveis",
        "Quadro base para análise da origem e do destino dos valores dentro da proposta.",
    )

    if itens.empty:
        st.warning("Esta proposta não possui itens disponíveis para remanejamento.")
        return

    itens_exibir = itens.copy()
    for col in ["valor_unitario", "valor_total", "valor_autorizado", "valor_remanejavel", "valor_pago_total"]:
        if col in itens_exibir.columns:
            itens_exibir[col] = itens_exibir[col].apply(_formatar_moeda)

    render_html_table(
        itens_exibir[
            [
                "id",
                "codigo_procedimento",
                "descricao_procedimento",
                "quantidade_autorizada",
                "qtd_exec_hospitalar",
                "qtd_exec_ambulatorial",
                "qtd_executada_total",
                "qtd_remanejavel",
                "valor_unitario",
                "valor_autorizado",
                "valor_remanejavel",
                "valor_pago_total",
            ]
        ].rename(
            columns={
                "id": "ID",
                "codigo_procedimento": "CÓDIGO",
                "descricao_procedimento": "DESCRIÇÃO",
                "quantidade_autorizada": "QTD. AUTORIZADA",
                "qtd_exec_hospitalar": "EXEC. HOSP",
                "qtd_exec_ambulatorial": "EXEC. AMB",
                "qtd_executada_total": "EXEC. TOTAL",
                "qtd_remanejavel": "QTD. REMANEJÁVEL",
                "valor_unitario": "VALOR UNITÁRIO",
                "valor_autorizado": "VALOR AUTORIZADO",
                "valor_remanejavel": "VALOR REMANEJÁVEL",
                "valor_pago_total": "VALOR PAGO",
            }
        )
    )

    section_header(
        "Simular e efetivar remanejamento",
        "Selecione item de origem, item de destino e a quantidade a ser redistribuída.",
    )

    itens_origem = itens[itens["qtd_remanejavel"] > 0].copy()
    itens_destino = itens.copy()

    if itens_origem.empty or itens_destino.empty:
        st.info("Não há combinação disponível para realizar remanejamento.")
    else:
        origem_map = {
            f"{row['id']} | {row['codigo_procedimento']} | saldo: {int(row['qtd_remanejavel'])}": int(row["id"])
            for _, row in itens_origem.iterrows()
        }
        destino_map = {
            f"{row['id']} | {row['codigo_procedimento']} | {row['descricao_procedimento']}": int(row["id"])
            for _, row in itens_destino.iterrows()
        }

        with st.form("form_remanejamento"):
            c1, c2 = st.columns(2)
            origem_label = c1.selectbox("Item de origem", list(origem_map.keys()))
            destino_label = c2.selectbox("Item de destino", list(destino_map.keys()))

            origem_id = origem_map[origem_label]
            destino_id = destino_map[destino_label]

            origem_row = itens_origem[itens_origem["id"] == origem_id].iloc[0]
            saldo_qtd = int(origem_row["qtd_remanejavel"] or 0)

            if saldo_qtd < 1:
                saldo_qtd = 1

            quantidade = st.number_input(
                "Quantidade a remanejar da origem",
                min_value=1,
                max_value=saldo_qtd,
                value=1,
                step=1,
            )

            justificativa = st.text_area("Justificativa")
            observacao = st.text_area("Observação complementar")

            simular = st.form_submit_button("Simular remanejamento", use_container_width=True)
            efetivar = st.form_submit_button("Efetivar remanejamento", use_container_width=True)

            if simular:
                ok, msg, simulacao = simular_remanejamento(
                    proposta_id=proposta_id,
                    item_origem_id=origem_id,
                    item_destino_id=destino_id,
                    quantidade_origem_remanejada=int(quantidade),
                )
                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)

                if simulacao:
                    status_badge("Simulação concluída", "info")

                    d1, d2, d3 = st.columns(3)
                    with d1:
                        kpi_card(
                            "Valor remanejado da origem",
                            _formatar_moeda(simulacao["movimento"]["valor_origem_remanejado"]),
                        )
                    with d2:
                        kpi_card(
                            "Qtd. acrescida no destino",
                            str(simulacao["movimento"]["quantidade_destino_acrescida"]),
                        )
                    with d3:
                        kpi_card(
                            "Saldo residual",
                            _formatar_moeda(simulacao["movimento"]["saldo_residual"]),
                        )

                    st.markdown(
                        f"""
                        **Origem:** {simulacao['origem']['codigo']} - {simulacao['origem']['descricao']}  
                        **Qtd. autorizada atual:** {simulacao['origem']['quantidade_autorizada_atual']}  
                        **Qtd. autorizada nova:** {simulacao['origem']['quantidade_autorizada_nova']}  
                        **Destino:** {simulacao['destino']['codigo']} - {simulacao['destino']['descricao']}  
                        **Qtd. autorizada atual (destino):** {simulacao['destino']['quantidade_autorizada_atual']}  
                        **Qtd. autorizada nova (destino):** {simulacao['destino']['quantidade_autorizada_nova']}
                        """
                    )

                    if simulacao["alertas"]["possui_pagamento_origem"]:
                        status_badge("A origem já possui pagamento registrado", "warning")
                    if simulacao["alertas"]["origem_muito_comprometida"]:
                        status_badge("A origem está muito comprometida pela execução", "warning")

            if efetivar:
                if origem_id == destino_id:
                    st.error("O item de origem não pode ser igual ao item de destino.")
                else:
                    ok, msg = efetivar_remanejamento(
                        proposta_id=proposta_id,
                        item_origem_id=origem_id,
                        item_destino_id=destino_id,
                        quantidade_origem_remanejada=int(quantidade),
                        justificativa=justificativa,
                        observacao=observacao,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    section_header(
        "Histórico de remanejamentos",
        "Relação das movimentações já registradas para a proposta selecionada.",
    )

    historico = listar_historico_remanejamentos(proposta_id)
    if historico.empty:
        st.info("Nenhum remanejamento registrado para esta proposta.")
    else:
        historico_exibir = historico.copy()
        for col in [
            "valor_origem_remanejado",
            "valor_destino_acrescido",
            "saldo_residual",
        ]:
            if col in historico_exibir.columns:
                historico_exibir[col] = historico_exibir[col].apply(_formatar_moeda)

        render_html_table(
            historico_exibir.rename(
                columns={
                    "created_at": "CRIADO EM",
                    "usuario": "USUÁRIO",
                    "item_origem_codigo": "CÓDIGO ORIGEM",
                    "item_origem_descricao": "DESCRIÇÃO ORIGEM",
                    "item_destino_codigo": "CÓDIGO DESTINO",
                    "item_destino_descricao": "DESCRIÇÃO DESTINO",
                    "quantidade_origem_remanejada": "QTD. REMANEJADA",
                    "quantidade_destino_acrescida": "QTD. DESTINO ACRESCIDA",
                    "valor_origem_remanejado": "VALOR ORIGEM",
                    "valor_destino_acrescido": "VALOR DESTINO",
                    "saldo_residual": "SALDO RESIDUAL",
                    "justificativa": "JUSTIFICATIVA",
                    "observacao": "OBSERVAÇÃO",
                }
            )
        )
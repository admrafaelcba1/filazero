import pandas as pd
import streamlit as st

from services.alerta_service import listar_alertas_proposta_df
from services.auditoria_service import listar_auditoria_proposta
from services.execucao_service import listar_execucoes_proposta
from services.exportacao_service import exportar_propostas_excel
from services.fase_service import obter_contexto_fase_proposta
from services.pagamento_service import listar_pagamentos_proposta
from services.proposta_service import (
    ORIGENS_RECURSO_PADRAO,
    STATUS_PROPOSTA,
    adicionar_item_proposta,
    atualizar_status_proposta,
    autorizar_item,
    buscar_catalogo_para_select,
    criar_proposta,
    excluir_item,
    gerar_numero_proposta_automatico,
    listar_itens_da_proposta,
    listar_proponentes_opcoes,
    listar_propostas,
    obter_proposta,
)
from utils.layout import (
    info_strip,
    kpi_card,
    page_header,
    render_html_table,
    section_header,
    status_badge,
    status_variant_from_text,
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


def _definir_situacao_item(row) -> str:
    qtd = int(row.get("quantidade", 0) or 0)
    qtd_aut = int(row.get("quantidade_autorizada", 0) or 0)
    qtd_exec = int(row.get("quantidade_executada", 0) or 0)
    valor_exec = float(row.get("valor_executado", 0) or 0)
    valor_pago = float(row.get("valor_pago", 0) or 0)

    if qtd <= 0:
        return "SEM QUANTIDADE"
    if qtd_aut <= 0:
        return "NÃO AUTORIZADO"
    if qtd_exec <= 0:
        return "AUTORIZADO PARCIAL" if qtd_aut < qtd else "AUTORIZADO"
    if valor_pago <= 0:
        return "EM EXECUÇÃO" if qtd_exec < qtd_aut else "EXECUTADO"
    if valor_pago < valor_exec:
        return "PAGAMENTO PARCIAL"
    return "PAGO"


def _obter_resumo_consolidado_proposta(proposta_id: int, itens: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    if itens is None or itens.empty:
        resumo = {
            "valor_proposto": 0.0,
            "valor_autorizado": 0.0,
            "valor_executado": 0.0,
            "valor_pago": 0.0,
            "saldo_a_executar": 0.0,
            "saldo_a_pagar": 0.0,
            "quantidade_proposta": 0,
            "quantidade_autorizada": 0,
            "quantidade_executada": 0,
        }
        return resumo, pd.DataFrame()

    itens_calc = itens.copy()

    execucoes = listar_execucoes_proposta(proposta_id)
    pagamentos = listar_pagamentos_proposta(proposta_id)

    if execucoes.empty:
        exec_por_item = pd.DataFrame(columns=["item_proposta_id", "quantidade_executada", "valor_executado"])
    else:
        exec_por_item = (
            execucoes.groupby("item_proposta_id", as_index=False)
            .agg(
                quantidade_executada=("quantidade", "sum"),
                valor_executado=("valor_total", "sum"),
            )
        )

    if pagamentos.empty:
        pag_por_item = pd.DataFrame(columns=["item_proposta_id", "valor_pago"])
    else:
        pag_por_item = pagamentos.groupby("item_proposta_id", as_index=False).agg(valor_pago=("valor_pago", "sum"))

    itens_calc = itens_calc.merge(exec_por_item, how="left", left_on="id", right_on="item_proposta_id")
    itens_calc = itens_calc.merge(
        pag_por_item,
        how="left",
        left_on="id",
        right_on="item_proposta_id",
        suffixes=("", "_pag"),
    )

    itens_calc["quantidade_executada"] = itens_calc["quantidade_executada"].fillna(0).astype(int)
    itens_calc["valor_executado"] = itens_calc["valor_executado"].fillna(0.0)
    itens_calc["valor_pago"] = itens_calc["valor_pago"].fillna(0.0)

    itens_calc["saldo_quantidade_execucao"] = (
        itens_calc["quantidade_autorizada"].fillna(0) - itens_calc["quantidade_executada"].fillna(0)
    )
    itens_calc["saldo_valor_execucao"] = (
        itens_calc["valor_autorizado"].fillna(0) - itens_calc["valor_executado"].fillna(0)
    )
    itens_calc["saldo_valor_pagamento"] = itens_calc["valor_executado"].fillna(0) - itens_calc["valor_pago"].fillna(0)
    itens_calc["possui_execucao"] = itens_calc["quantidade_executada"].fillna(0) > 0
    itens_calc["possui_pagamento"] = itens_calc["valor_pago"].fillna(0) > 0
    itens_calc["situacao_item"] = itens_calc.apply(_definir_situacao_item, axis=1)

    resumo = {
        "valor_proposto": float(itens_calc["valor_total"].fillna(0).sum()),
        "valor_autorizado": float(itens_calc["valor_autorizado"].fillna(0).sum()),
        "valor_executado": float(itens_calc["valor_executado"].fillna(0).sum()),
        "valor_pago": float(itens_calc["valor_pago"].fillna(0).sum()),
        "saldo_a_executar": float(itens_calc["saldo_valor_execucao"].fillna(0).sum()),
        "saldo_a_pagar": float(itens_calc["saldo_valor_pagamento"].fillna(0).sum()),
        "quantidade_proposta": int(itens_calc["quantidade"].fillna(0).sum()),
        "quantidade_autorizada": int(itens_calc["quantidade_autorizada"].fillna(0).sum()),
        "quantidade_executada": int(itens_calc["quantidade_executada"].fillna(0).sum()),
    }

    return resumo, itens_calc


def render():
    page_header(
        "Propostas e autorização",
        "Cadastro, autorização, consolidação, alertas e auditoria por proposta.",
        tag="Núcleo do sistema",
    )

    info_strip(
        "Esta tela concentra o ciclo administrativo da proposta: criação, inclusão de itens, autorização, "
        "acompanhamento consolidado, atualização de status e auditoria."
    )

    tab1, tab2 = st.tabs(["Nova Proposta", "Gerenciar Proposta"])

    with tab1:
        section_header(
            "Cadastrar nova proposta",
            "Registro inicial da proposta com numeração, competência, proponente e origem do recurso.",
        )

        proponentes = listar_proponentes_opcoes()
        mapa_proponentes = {row["proponente"]: int(row["id"]) for _, row in proponentes.iterrows()}

        ano_padrao = 2026
        numero_sugerido = gerar_numero_proposta_automatico(ano_padrao)

        with st.form("form_nova_proposta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            numero_proposta = c1.text_input("Nº da proposta", value=numero_sugerido)
            competencia_mes = c2.selectbox("Competência - mês", list(MESES.keys()), format_func=lambda x: MESES[x])
            competencia_ano = c3.number_input("Competência - ano", min_value=2024, max_value=2100, value=ano_padrao, step=1)

            c4, c5, c6 = st.columns(3)
            proponente = c4.selectbox("PROPONENTE", options=[""] + list(mapa_proponentes.keys()))
            ordem_proposta = c5.number_input("Ordem da proposta do proponente", min_value=1, step=1, value=1)
            status = c6.selectbox("STATUS", STATUS_PROPOSTA, index=0)

            c7, c8 = st.columns(2)
            origem_recurso = c7.selectbox("Origem do recurso", options=[""] + ORIGENS_RECURSO_PADRAO)
            deputado = c8.text_input("Deputado(a)")

            observacao = st.text_area("Observações")

            submitted = st.form_submit_button("Criar proposta", use_container_width=True)

            if submitted:
                proponente_id = mapa_proponentes.get(proponente) if proponente else None
                ok, msg, proposta_id = criar_proposta(
                    numero_proposta=numero_proposta,
                    proponente_id=proponente_id,
                    proponente=proponente,
                    ordem_proposta=int(ordem_proposta),
                    competencia_mes=int(competencia_mes),
                    competencia_ano=int(competencia_ano),
                    origem_recurso=origem_recurso,
                    deputado=deputado,
                    status=status,
                    observacao=observacao,
                )
                if ok:
                    st.success(msg)
                    st.session_state["proposta_selecionada_id"] = proposta_id
                    st.rerun()
                else:
                    st.error(msg)

    with tab2:
        section_header(
            "Gerenciar proposta",
            "Seleção, filtros, consolidação, autorização, status e histórico da proposta.",
        )

        df_prop = listar_propostas()
        if df_prop.empty:
            st.info("Cadastre uma proposta antes de gerenciar.")
            return

        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        filtro_proponente = f1.selectbox(
            "Filtrar por proponente",
            options=[None] + sorted(df_prop["proponente"].dropna().unique().tolist()),
            format_func=lambda x: "Todos" if x is None else x,
        )
        filtro_status = f2.selectbox(
            "Filtrar por status",
            options=[None] + STATUS_PROPOSTA,
            format_func=lambda x: "Todos" if x is None else x,
        )
        filtro_ano = f3.selectbox(
            "Filtrar por ano",
            options=[None] + sorted(df_prop["competencia_ano"].dropna().unique().tolist(), reverse=True),
            format_func=lambda x: "Todos" if x is None else str(x),
        )

        excel = exportar_propostas_excel(
            competencia_ano=filtro_ano,
            status=filtro_status,
            proponente=filtro_proponente,
        )
        f4.download_button(
            "Exportar Excel",
            data=excel,
            file_name="propostas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        if filtro_proponente:
            df_prop = df_prop[df_prop["proponente"] == filtro_proponente]
        if filtro_status:
            df_prop = df_prop[df_prop["status"] == filtro_status]
        if filtro_ano:
            df_prop = df_prop[df_prop["competencia_ano"] == filtro_ano]

        if df_prop.empty:
            st.info("Nenhuma proposta encontrada com os filtros informados.")
            return

        opcoes = {
            f"{row['numero_proposta']} | {row['proponente']} | {row['ordem_proposta']}ª": int(row["id"])
            for _, row in df_prop.iterrows()
        }

        proposta_id_state = st.session_state.get("proposta_selecionada_id")
        proposta_label_default = None
        if proposta_id_state:
            for label, pid in opcoes.items():
                if pid == proposta_id_state:
                    proposta_label_default = label
                    break

        labels = list(opcoes.keys())
        index_default = labels.index(proposta_label_default) if proposta_label_default in labels else 0

        proposta_label = st.selectbox("Selecione a proposta", labels, index=index_default)
        proposta_id = opcoes[proposta_label]
        st.session_state["proposta_selecionada_id"] = proposta_id

        proposta = obter_proposta(proposta_id)
        itens = listar_itens_da_proposta(proposta_id)
        resumo, itens_consolidados = _obter_resumo_consolidado_proposta(proposta_id, itens)
        contexto = obter_contexto_fase_proposta(proposta_id)
        alertas_df = listar_alertas_proposta_df(proposta_id)

        section_header(
            "Resumo institucional da proposta",
            "Leitura executiva do número, proponente, status e posição financeira da proposta selecionada.",
        )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi_card("Nº da proposta", proposta["numero_proposta"] or "-")
        with k2:
            kpi_card("Proponente", proposta["proponente"] or "-")
        with k3:
            kpi_card("Ordem", f"{int(proposta['ordem_proposta'] or 1)}ª")
        with k4:
            kpi_card("Status", proposta["status"] or "-")

        status_badge(proposta["status"] or "SEM STATUS", status_variant_from_text(proposta["status"] or ""))

        k5, k6, k7, k8 = st.columns(4)
        with k5:
            kpi_card("Qtd. proposta", str(int(proposta["quantidade_proposta"] or 0)))
        with k6:
            kpi_card("Proc. diversos", str(int(proposta["quantidade_proc_diversos"] or 0)))
        with k7:
            kpi_card("Cirurgia", str(int(proposta["quantidade_cirurgia"] or 0)))
        with k8:
            kpi_card("Valor total", _formatar_moeda(proposta["valor_total"]))

        st.markdown(
            f"""
            **Origem do recurso:** {proposta.get('origem_recurso') or '-'}  
            **Deputado(a):** {proposta.get('deputado') or '-'}  
            **Competência:** {MESES.get(int(proposta['competencia_mes'] or 0), '-')} / {proposta.get('competencia_ano') or '-'}
            """
        )

        section_header(
            "Fase e alertas da proposta",
            "Contexto operacional da proposta, com leitura dos bloqueios e inconsistências identificadas.",
        )

        if contexto["mensagem_edicao"]:
            st.warning(contexto["mensagem_edicao"])
        else:
            status_badge("A proposta está em fase compatível com edição/autorização.", "success")

        if alertas_df.empty:
            status_badge("Nenhum alerta operacional identificado nesta proposta.", "success")
        else:
            st.warning(f"Foram encontrados {len(alertas_df)} alerta(s) nesta proposta.")
            render_html_table(alertas_df[["nivel", "codigo", "mensagem"]])

        section_header(
            "Visão consolidada da proposta",
            "Síntese financeira e quantitativa dos itens, da autorização, da execução e do pagamento.",
        )

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            kpi_card("Valor proposto", _formatar_moeda(resumo["valor_proposto"]))
        with r2:
            kpi_card("Valor autorizado", _formatar_moeda(resumo["valor_autorizado"]))
        with r3:
            kpi_card("Valor executado", _formatar_moeda(resumo["valor_executado"]))
        with r4:
            kpi_card("Valor pago", _formatar_moeda(resumo["valor_pago"]))

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            kpi_card("Saldo a executar", _formatar_moeda(resumo["saldo_a_executar"]))
        with r6:
            kpi_card("Saldo a pagar", _formatar_moeda(resumo["saldo_a_pagar"]))
        with r7:
            kpi_card("Qtd. autorizada", str(int(resumo["quantidade_autorizada"])))
        with r8:
            kpi_card("Qtd. executada", str(int(resumo["quantidade_executada"])))

        if itens_consolidados.empty:
            st.info("Ainda não há itens para consolidar nesta proposta.")
        else:
            quadro = itens_consolidados.copy()
            for col in [
                "valor_unitario",
                "valor_total",
                "valor_autorizado",
                "valor_executado",
                "valor_pago",
                "saldo_valor_execucao",
                "saldo_valor_pagamento",
            ]:
                quadro[col] = quadro[col].apply(_formatar_moeda)

            quadro["uso_operacional"] = quadro.apply(
                lambda row: "EXECUÇÃO E PAGAMENTO"
                if row["possui_execucao"] and row["possui_pagamento"]
                else "EXECUÇÃO"
                if row["possui_execucao"]
                else "PAGAMENTO"
                if row["possui_pagamento"]
                else "-",
                axis=1,
            )

            render_html_table(
                quadro[
                    [
                        "id",
                        "codigo_procedimento",
                        "descricao_procedimento",
                        "natureza",
                        "quantidade",
                        "quantidade_autorizada",
                        "quantidade_executada",
                        "valor_unitario",
                        "valor_total",
                        "valor_autorizado",
                        "valor_executado",
                        "valor_pago",
                        "saldo_quantidade_execucao",
                        "saldo_valor_execucao",
                        "saldo_valor_pagamento",
                        "uso_operacional",
                        "situacao_item",
                    ]
                ].rename(
                    columns={
                        "id": "ID",
                        "codigo_procedimento": "CÓDIGO",
                        "descricao_procedimento": "DESCRIÇÃO",
                        "natureza": "NATUREZA",
                        "quantidade": "QTD. PROPOSTA",
                        "quantidade_autorizada": "QTD. AUTORIZADA",
                        "quantidade_executada": "QTD. EXECUTADA",
                        "valor_unitario": "VALOR UNITÁRIO",
                        "valor_total": "VALOR TOTAL",
                        "valor_autorizado": "VALOR AUTORIZADO",
                        "valor_executado": "VALOR EXECUTADO",
                        "valor_pago": "VALOR PAGO",
                        "saldo_quantidade_execucao": "SALDO QTD.",
                        "saldo_valor_execucao": "SALDO EXECUÇÃO",
                        "saldo_valor_pagamento": "SALDO PAGAMENTO",
                        "uso_operacional": "USO OPERACIONAL",
                        "situacao_item": "SITUAÇÃO",
                    }
                )
            )

        section_header(
            "Adicionar item à proposta",
            "Inclusão de novos procedimentos enquanto a fase da proposta permitir alteração estrutural.",
        )

        if not contexto["pode_adicionar_item"]:
            st.info("Inclusão de itens bloqueada para a fase atual da proposta.")
        else:
            filtro = st.text_input("Pesquisar procedimento por código ou descrição", key="filtro_catalogo_proposta")
            df_catalogo = buscar_catalogo_para_select(filtro)

            if df_catalogo.empty:
                st.warning("Nenhum procedimento encontrado no catálogo.")
            else:
                mapa_proc = {
                    f"{row['codigo']} - {row['descricao']}": row["codigo"]
                    for _, row in df_catalogo.iterrows()
                }

                with st.form("form_add_item", clear_on_submit=True):
                    proc_label = st.selectbox("Procedimento", list(mapa_proc.keys()))
                    codigo = mapa_proc[proc_label]
                    proc = df_catalogo[df_catalogo["codigo"] == codigo].iloc[0]

                    a1, a2, a3, a4 = st.columns(4)
                    a1.text_input("CÓDIGO SIGTAP", value=str(proc["codigo"]), disabled=True)
                    a2.text_input("CLASSIFICAÇÃO", value=str(proc["classificacao"] or ""), disabled=True)
                    a3.text_input("NATUREZA", value=str(proc["natureza"] or ""), disabled=True)
                    a4.text_input("SUBGRUPO", value=str(proc["subgrupo"] or ""), disabled=True)

                    st.text_input("DESCRIÇÃO DO PROCEDIMENTO", value=str(proc["descricao"]), disabled=True)
                    b1, b2, b3 = st.columns(3)
                    b1.number_input("VALOR UNITÁRIO", value=float(proc["valor_unitario"] or 0), disabled=True)
                    quantidade = b2.number_input("QTDD. PROPOSTA", min_value=1, step=1, value=1)
                    valor_previsto = float(proc["valor_unitario"] or 0) * int(quantidade)
                    b3.number_input("VALOR", value=valor_previsto, disabled=True)

                    submitted_item = st.form_submit_button("Adicionar item", use_container_width=True)

                    if submitted_item:
                        ok, msg = adicionar_item_proposta(
                            proposta_id=proposta_id,
                            codigo_procedimento=codigo,
                            quantidade=int(quantidade),
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        section_header(
            "Itens da proposta",
            "Quadro detalhado dos itens lançados, seus quantitativos, autorização e situação operacional.",
        )

        if itens.empty:
            st.info("Nenhum item cadastrado nesta proposta.")
        else:
            itens_exibir = itens.copy()
            itens_exibir["valor_unitario"] = itens_exibir["valor_unitario"].apply(_formatar_moeda)
            itens_exibir["valor_total"] = itens_exibir["valor_total"].apply(_formatar_moeda)
            itens_exibir["valor_autorizado"] = itens_exibir["valor_autorizado"].apply(_formatar_moeda)

            if not itens_consolidados.empty:
                uso_cols = itens_consolidados[
                    ["id", "quantidade_executada", "valor_pago", "situacao_item", "possui_execucao", "possui_pagamento"]
                ].copy()
                itens_exibir = itens_exibir.merge(uso_cols, how="left", on="id")
                itens_exibir["quantidade_executada"] = itens_exibir["quantidade_executada"].fillna(0).astype(int)
                itens_exibir["valor_pago"] = itens_exibir["valor_pago"].fillna(0.0)
                itens_exibir["possui_execucao"] = itens_exibir["possui_execucao"].fillna(False)
                itens_exibir["possui_pagamento"] = itens_exibir["possui_pagamento"].fillna(False)
                itens_exibir["valor_pago"] = itens_exibir["valor_pago"].apply(_formatar_moeda)
            else:
                itens_exibir["quantidade_executada"] = 0
                itens_exibir["valor_pago"] = _formatar_moeda(0)
                itens_exibir["situacao_item"] = "-"
                itens_exibir["possui_execucao"] = False
                itens_exibir["possui_pagamento"] = False

            render_html_table(
                itens_exibir[
                    [
                        "id",
                        "codigo_procedimento",
                        "descricao_procedimento",
                        "classificacao",
                        "subgrupo",
                        "natureza",
                        "quantidade",
                        "quantidade_autorizada",
                        "quantidade_executada",
                        "valor_unitario",
                        "valor_total",
                        "valor_autorizado",
                        "valor_pago",
                        "situacao_item",
                    ]
                ].rename(
                    columns={
                        "id": "ID",
                        "codigo_procedimento": "CÓDIGO",
                        "descricao_procedimento": "DESCRIÇÃO",
                        "classificacao": "CLASSIFICAÇÃO",
                        "subgrupo": "SUBGRUPO",
                        "natureza": "NATUREZA",
                        "quantidade": "QTD. PROPOSTA",
                        "quantidade_autorizada": "QTD. AUTORIZADA",
                        "quantidade_executada": "QTD. EXECUTADA",
                        "valor_unitario": "VALOR UNITÁRIO",
                        "valor_total": "VALOR TOTAL",
                        "valor_autorizado": "VALOR AUTORIZADO",
                        "valor_pago": "VALOR PAGO",
                        "situacao_item": "SITUAÇÃO",
                    }
                )
            )

            st.markdown("### Autorizar item")

            item_map = {
                f"{row['id']} | {row['codigo_procedimento']} | {row['descricao_procedimento']}": int(row["id"])
                for _, row in itens.iterrows()
            }

            item_label = st.selectbox("Item", list(item_map.keys()), key="proposta_item_select")
            item_id = item_map[item_label]
            item_row = itens[itens["id"] == item_id].iloc[0]

            item_operacional = None
            if not itens_consolidados.empty:
                filtro_item = itens_consolidados[itens_consolidados["id"] == item_id]
                if not filtro_item.empty:
                    item_operacional = filtro_item.iloc[0]

            qtd_executada_item = int(item_operacional["quantidade_executada"]) if item_operacional is not None else 0
            valor_pago_item = float(item_operacional["valor_pago"]) if item_operacional is not None else 0.0
            possui_execucao = bool(item_operacional["possui_execucao"]) if item_operacional is not None else False
            possui_pagamento = bool(item_operacional["possui_pagamento"]) if item_operacional is not None else False

            if possui_execucao:
                st.warning(f"Este item já possui execução registrada. Quantidade já executada: {qtd_executada_item}.")
            if possui_pagamento:
                st.warning(f"Este item já possui pagamento registrado no total de {_formatar_moeda(valor_pago_item)}.")

            qtd_minima_autorizacao = qtd_executada_item if qtd_executada_item > 0 else 0
            exclusao_bloqueada = (not contexto["pode_excluir_item"]) or possui_execucao or possui_pagamento
            autorizacao_bloqueada = not contexto["pode_autorizar_item"]

            with st.form("form_autorizar_item"):
                d1, d2, d3 = st.columns(3)
                d1.number_input("QTDD. PROPOSTA", value=int(item_row["quantidade"]), disabled=True)
                qtd_aut = d2.number_input(
                    "CIRURGIA",
                    min_value=int(qtd_minima_autorizacao),
                    max_value=int(item_row["quantidade"]),
                    value=max(int(item_row["quantidade_autorizada"] or 0), int(qtd_minima_autorizacao)),
                    step=1,
                    disabled=autorizacao_bloqueada,
                )
                d3.number_input(
                    "VALOR AUTORIZADO",
                    value=float(item_row["valor_unitario"] or 0) * int(qtd_aut),
                    disabled=True,
                )

                if qtd_executada_item > 0:
                    st.info(
                        f"A autorização mínima permitida para este item é {qtd_executada_item}, "
                        "pois já existe execução registrada."
                    )

                if autorizacao_bloqueada:
                    st.info("Autorização bloqueada para a fase atual da proposta.")

                col_a, col_b = st.columns(2)
                salvar_aut = col_a.form_submit_button(
                    "Salvar autorização",
                    use_container_width=True,
                    disabled=autorizacao_bloqueada,
                )
                excluir = col_b.form_submit_button(
                    "Excluir item" if not exclusao_bloqueada else "Exclusão bloqueada",
                    use_container_width=True,
                    disabled=exclusao_bloqueada,
                )

                if salvar_aut:
                    ok, msg = autorizar_item(item_id=item_id, quantidade_autorizada=int(qtd_aut))
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                if excluir:
                    ok, msg = excluir_item(item_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        section_header(
            "Status e parecer técnico",
            "Atualização manual do status administrativo e do parecer técnico da proposta.",
        )

        with st.form("form_status_proposta"):
            novo_status = st.selectbox(
                "STATUS",
                STATUS_PROPOSTA,
                index=STATUS_PROPOSTA.index(proposta["status"]) if proposta["status"] in STATUS_PROPOSTA else 0,
            )
            parecer = st.text_area("Parecer técnico", value=proposta.get("parecer_tecnico") or "")
            submit_status = st.form_submit_button("Atualizar status", use_container_width=True)

            if submit_status:
                ok, msg = atualizar_status_proposta(
                    proposta_id=proposta_id,
                    status=novo_status,
                    parecer_tecnico=parecer,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        section_header(
            "Histórico de auditoria da proposta",
            "Rastro das principais movimentações registradas na proposta e em seus itens.",
        )

        df_auditoria = listar_auditoria_proposta(proposta_id)

        if df_auditoria.empty:
            st.info("Nenhum registro de auditoria para esta proposta.")
        else:
            df_auditoria_exibir = df_auditoria.copy()
            df_auditoria_exibir["created_at"] = pd.to_datetime(
                df_auditoria_exibir["created_at"], errors="coerce"
            ).dt.strftime("%d/%m/%Y %H:%M")
            df_auditoria_exibir["acao"] = df_auditoria_exibir["acao"].fillna("").str.replace("_", " ")
            df_auditoria_exibir["entidade"] = df_auditoria_exibir["entidade"].fillna("").str.replace("_", " ")

            render_html_table(
                df_auditoria_exibir[
                    [
                        "created_at",
                        "acao",
                        "entidade",
                        "item_id",
                        "usuario",
                        "detalhes",
                    ]
                ].rename(
                    columns={
                        "created_at": "DATA/HORA",
                        "acao": "AÇÃO",
                        "entidade": "ENTIDADE",
                        "item_id": "ITEM",
                        "usuario": "USUÁRIO",
                        "detalhes": "DETALHES",
                    }
                )
            )
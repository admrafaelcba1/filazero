import pandas as pd
import streamlit as st

from services.painel_executivo_service import obter_painel_executivo
from utils.layout import (
    info_strip,
    kpi_card,
    page_header,
    progress_card,
    render_html_table,
    section_header,
    status_badge,
    status_variant_from_text,
)


def _formatar_moeda(valor) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _aplicar_filtros_df(
    df: pd.DataFrame,
    filtro_proponente=None,
    filtro_status=None,
    filtro_ano=None,
    filtro_mes=None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    filtrado = df.copy()

    if filtro_proponente is not None and "proponente" in filtrado.columns:
        filtrado = filtrado[filtrado["proponente"] == filtro_proponente]

    if filtro_status is not None and "status" in filtrado.columns:
        filtrado = filtrado[filtrado["status"] == filtro_status]

    if filtro_ano is not None and "competencia_ano" in filtrado.columns:
        filtrado = filtrado[filtrado["competencia_ano"] == filtro_ano]

    if filtro_mes is not None and "competencia_mes" in filtrado.columns:
        filtrado = filtrado[filtrado["competencia_mes"] == filtro_mes]

    return filtrado


def _recalcular_metricas_base(df_base: pd.DataFrame) -> dict:
    if df_base is None or df_base.empty:
        return {
            "total_propostas": 0,
            "total_autorizado": 0.0,
            "total_executado": 0.0,
            "total_pago": 0.0,
            "saldo_a_executar": 0.0,
            "saldo_a_pagar": 0.0,
        }

    total_propostas = int(df_base["proposta_id"].nunique()) if "proposta_id" in df_base.columns else 0
    total_autorizado = float(df_base["valor_autorizado"].fillna(0).sum()) if "valor_autorizado" in df_base.columns else 0.0
    total_executado = float(df_base["valor_executado"].fillna(0).sum()) if "valor_executado" in df_base.columns else 0.0
    total_pago = float(df_base["valor_pago"].fillna(0).sum()) if "valor_pago" in df_base.columns else 0.0

    return {
        "total_propostas": total_propostas,
        "total_autorizado": total_autorizado,
        "total_executado": total_executado,
        "total_pago": total_pago,
        "saldo_a_executar": total_autorizado - total_executado,
        "saldo_a_pagar": total_executado - total_pago,
    }


def _recalcular_status_df(df_base: pd.DataFrame) -> pd.DataFrame:
    if df_base is None or df_base.empty or "status" not in df_base.columns:
        return pd.DataFrame()

    agg = (
        df_base.groupby("status", dropna=False, as_index=False)
        .agg(
            total_propostas=("proposta_id", "nunique"),
            valor_autorizado=("valor_autorizado", "sum"),
            valor_executado=("valor_executado", "sum"),
            valor_pago=("valor_pago", "sum"),
        )
        .sort_values("total_propostas", ascending=False)
    )

    agg["status"] = agg["status"].fillna("SEM STATUS")
    return agg


def _recalcular_top(
    df_base: pd.DataFrame,
    group_col: str,
    value_col: str,
    output_name: str,
    top_n: int = 10,
) -> pd.DataFrame:
    if df_base is None or df_base.empty or group_col not in df_base.columns or value_col not in df_base.columns:
        return pd.DataFrame()

    df = (
        df_base.groupby(group_col, dropna=False, as_index=False)[value_col]
        .sum()
        .rename(columns={group_col: output_name})
        .sort_values(value_col, ascending=False)
        .head(top_n)
    )

    df[output_name] = df[output_name].fillna("NÃO INFORMADO")
    return df


def _recalcular_top_propostas(
    df_base: pd.DataFrame,
    value_col: str,
    output_value_name: str,
    top_n: int = 10,
) -> pd.DataFrame:
    required = ["numero_proposta", "proponente", value_col]
    if df_base is None or df_base.empty or any(c not in df_base.columns for c in required):
        return pd.DataFrame()

    df = (
        df_base.groupby(["numero_proposta", "proponente"], dropna=False, as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: output_value_name})
        .sort_values(output_value_name, ascending=False)
        .head(top_n)
    )

    df["numero_proposta"] = df["numero_proposta"].fillna("SEM NÚMERO")
    df["proponente"] = df["proponente"].fillna("NÃO INFORMADO")
    return df


def render():
    page_header(
        "Painel Executivo",
        "Visão gerencial consolidada do Sistema Fila Zero na Cirurgia, com indicadores financeiros e operacionais do programa.",
        tag="Visão estratégica",
    )

    info_strip(
        "Este painel resume a situação global do programa e facilita a leitura rápida de saldos, gargalos operacionais, "
        "propostas com alerta, desempenho financeiro e concentração de resultados."
    )

    painel = obter_painel_executivo()

    base_df = painel.get("base_df", pd.DataFrame()).copy()
    status_df_original = painel.get("status_df", pd.DataFrame()).copy()
    alertas_df_original = painel.get("alertas_df", pd.DataFrame()).copy()

    section_header(
        "Filtros gerenciais",
        "Refine a visão do painel por proponente, status e competência.",
    )

    proponentes = []
    status_opcoes = []
    anos = []
    meses = []

    if not base_df.empty:
        if "proponente" in base_df.columns:
            proponentes = sorted([x for x in base_df["proponente"].dropna().unique().tolist() if str(x).strip()])
        if "status" in base_df.columns:
            status_opcoes = sorted([x for x in base_df["status"].dropna().unique().tolist() if str(x).strip()])
        if "competencia_ano" in base_df.columns:
            anos = sorted(base_df["competencia_ano"].dropna().unique().tolist(), reverse=True)
        if "competencia_mes" in base_df.columns:
            meses = sorted(base_df["competencia_mes"].dropna().unique().tolist())

    f1, f2, f3, f4 = st.columns(4)
    filtro_proponente = f1.selectbox(
        "Proponente",
        options=[None] + proponentes,
        format_func=lambda x: "Todos" if x is None else str(x),
    )
    filtro_status = f2.selectbox(
        "Status",
        options=[None] + status_opcoes,
        format_func=lambda x: "Todos" if x is None else str(x),
    )
    filtro_ano = f3.selectbox(
        "Ano",
        options=[None] + anos,
        format_func=lambda x: "Todos" if x is None else str(x),
    )
    filtro_mes = f4.selectbox(
        "Mês",
        options=[None] + meses,
        format_func=lambda x: "Todos" if x is None else f"{int(x):02d}",
    )

    base_filtrada = _aplicar_filtros_df(
        base_df,
        filtro_proponente=filtro_proponente,
        filtro_status=filtro_status,
        filtro_ano=filtro_ano,
        filtro_mes=filtro_mes,
    )

    metricas = _recalcular_metricas_base(base_filtrada)
    status_df = _recalcular_status_df(base_filtrada)

    top_proponentes_df = _recalcular_top(
        base_filtrada,
        group_col="proponente",
        value_col="valor_autorizado",
        output_name="proponente",
    )

    top_executores_df = _recalcular_top(
        base_filtrada,
        group_col="executor",
        value_col="valor_executado",
        output_name="executor",
    )

    top_propostas_pagas_df = _recalcular_top_propostas(
        base_filtrada,
        value_col="valor_pago",
        output_value_name="valor_pago",
    )

    top_saldo_pendente_df = _recalcular_top_propostas(
        base_filtrada.assign(
            saldo_pendente=base_filtrada.get("valor_autorizado", 0).fillna(0) - base_filtrada.get("valor_pago", 0).fillna(0)
            if not base_filtrada.empty and "valor_autorizado" in base_filtrada.columns and "valor_pago" in base_filtrada.columns
            else 0
        ),
        value_col="saldo_pendente",
        output_value_name="saldo_pendente",
    )

    alertas_df = alertas_df_original.copy()
    if not alertas_df.empty:
        if filtro_proponente is not None and "proponente" in alertas_df.columns:
            alertas_df = alertas_df[alertas_df["proponente"] == filtro_proponente]
        if filtro_status is not None and "status" in alertas_df.columns:
            alertas_df = alertas_df[alertas_df["status"] == filtro_status]
        if filtro_ano is not None and "competencia_ano" in alertas_df.columns:
            alertas_df = alertas_df[alertas_df["competencia_ano"] == filtro_ano]
        if filtro_mes is not None and "competencia_mes" in alertas_df.columns:
            alertas_df = alertas_df[alertas_df["competencia_mes"] == filtro_mes]

    total_alertas = len(alertas_df)
    alertas_altos = len(alertas_df[alertas_df["nivel"].astype(str).str.upper() == "ALTO"]) if not alertas_df.empty and "nivel" in alertas_df.columns else 0
    propostas_com_alerta = alertas_df["numero_proposta"].nunique() if not alertas_df.empty and "numero_proposta" in alertas_df.columns else 0

    section_header(
        "Indicadores financeiros principais",
        "Leitura executiva do comportamento financeiro consolidado das propostas.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Propostas", str(metricas["total_propostas"]), "Total de propostas no recorte selecionado.")
    with c2:
        kpi_card("Autorizado", _formatar_moeda(metricas["total_autorizado"]), "Valor total autorizado no recorte.")
    with c3:
        kpi_card("Executado", _formatar_moeda(metricas["total_executado"]), "Valor total executado no recorte.")
    with c4:
        kpi_card("Pago", _formatar_moeda(metricas["total_pago"]), "Valor total pago no recorte.")

    c5, c6 = st.columns(2)
    with c5:
        kpi_card("Saldo a executar", _formatar_moeda(metricas["saldo_a_executar"]), "Autorizado menos executado.")
    with c6:
        kpi_card("Saldo a pagar", _formatar_moeda(metricas["saldo_a_pagar"]), "Executado menos pago.")

    autorizado = float(metricas["total_autorizado"] or 0)
    executado = float(metricas["total_executado"] or 0)
    pago = float(metricas["total_pago"] or 0)

    perc_execucao = (executado / autorizado * 100) if autorizado > 0 else 0
    perc_pagamento = (pago / executado * 100) if executado > 0 else 0
    perc_pago_sobre_autorizado = (pago / autorizado * 100) if autorizado > 0 else 0

    section_header(
        "Eficiência financeira",
        "Leitura visual do aproveitamento do valor autorizado e da transformação da execução em pagamento.",
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        progress_card(
            "Execução sobre autorizado",
            perc_execucao,
            "Mostra quanto do valor autorizado já foi efetivamente executado.",
        )
    with p2:
        progress_card(
            "Pagamento sobre executado",
            perc_pagamento,
            "Mostra quanto do valor executado já foi convertido em pagamento.",
        )
    with p3:
        progress_card(
            "Pagamento sobre autorizado",
            perc_pago_sobre_autorizado,
            "Mostra o percentual total do autorizado que já foi pago.",
        )

    section_header(
        "Distribuição por status",
        "Consolidação das propostas por situação atual, com valores autorizados, executados e pagos.",
    )

    if status_df.empty:
        st.info("Sem dados para exibir.")
    else:
        status_exibir = status_df.copy()

        if "status" in status_exibir.columns:
            status_exibir["status_visual"] = status_exibir["status"].fillna("").apply(
                lambda s: f"<span class='fz-badge fz-badge-{status_variant_from_text(s)}'>{s}</span>"
            )

        for col in ["valor_autorizado", "valor_executado", "valor_pago"]:
            if col in status_exibir.columns:
                status_exibir[col] = status_exibir[col].apply(_formatar_moeda)

        status_exibir = status_exibir.rename(
            columns={
                "status_visual": "STATUS",
                "total_propostas": "TOTAL DE PROPOSTAS",
                "valor_autorizado": "VALOR AUTORIZADO",
                "valor_executado": "VALOR EXECUTADO",
                "valor_pago": "VALOR PAGO",
            }
        )

        cols = [c for c in ["STATUS", "TOTAL DE PROPOSTAS", "VALOR AUTORIZADO", "VALOR EXECUTADO", "VALOR PAGO"] if c in status_exibir.columns]
        render_html_table(status_exibir[cols])

    section_header(
        "Distribuição visual dos valores",
        "Comparação simples entre autorizado, executado e pago.",
    )

    grafico_df = pd.DataFrame(
        {
            "Etapa": ["Autorizado", "Executado", "Pago"],
            "Valor": [metricas["total_autorizado"], metricas["total_executado"], metricas["total_pago"]],
        }
    ).set_index("Etapa")

    st.bar_chart(grafico_df)

    section_header(
        "Rankings gerenciais",
        "Visões comparativas para apoio à tomada de decisão.",
    )

    r1, r2 = st.columns(2)

    with r1:
        st.markdown("#### Top proponentes por valor autorizado")
        if top_proponentes_df.empty:
            st.info("Sem dados.")
        else:
            df = top_proponentes_df.copy()
            if "valor_autorizado" in df.columns:
                df["valor_autorizado"] = df["valor_autorizado"].apply(_formatar_moeda)
            render_html_table(
                df.rename(
                    columns={
                        "proponente": "PROPONENTE",
                        "valor_autorizado": "VALOR AUTORIZADO",
                    }
                )
            )

        st.markdown("#### Top executores por valor executado")
        if top_executores_df.empty:
            st.info("Sem dados.")
        else:
            df = top_executores_df.copy()
            if "valor_executado" in df.columns:
                df["valor_executado"] = df["valor_executado"].apply(_formatar_moeda)
            render_html_table(
                df.rename(
                    columns={
                        "executor": "EXECUTOR",
                        "valor_executado": "VALOR EXECUTADO",
                    }
                )
            )

    with r2:
        st.markdown("#### Top propostas por valor pago")
        if top_propostas_pagas_df.empty:
            st.info("Sem dados.")
        else:
            df = top_propostas_pagas_df.copy()
            if "valor_pago" in df.columns:
                df["valor_pago"] = df["valor_pago"].apply(_formatar_moeda)
            render_html_table(
                df.rename(
                    columns={
                        "numero_proposta": "Nº PROPOSTA",
                        "proponente": "PROPONENTE",
                        "valor_pago": "VALOR PAGO",
                    }
                )
            )

        st.markdown("#### Top propostas com maior saldo pendente")
        if top_saldo_pendente_df.empty:
            st.info("Sem dados.")
        else:
            df = top_saldo_pendente_df.copy()
            if "saldo_pendente" in df.columns:
                df["saldo_pendente"] = df["saldo_pendente"].apply(_formatar_moeda)
            render_html_table(
                df.rename(
                    columns={
                        "numero_proposta": "Nº PROPOSTA",
                        "proponente": "PROPONENTE",
                        "saldo_pendente": "SALDO PENDENTE",
                    }
                )
            )

    section_header(
        "Alertas gerenciais",
        "Relação de inconsistências, riscos ou situações que exigem acompanhamento mais próximo.",
    )

    if alertas_df.empty:
        status_badge("Nenhum alerta operacional encontrado no momento.", "success")
    else:
        if alertas_altos > 0:
            status_badge(f"{alertas_altos} alerta(s) alto(s) identificado(s).", "danger")
        else:
            status_badge(f"{total_alertas} alerta(s) identificado(s).", "warning")

        st.markdown(
            f"""
            **Propostas com alerta:** {propostas_com_alerta}  
            **Total de alertas no recorte:** {total_alertas}
            """
        )

        render_html_table(
            alertas_df[
                [
                    "numero_proposta",
                    "proponente",
                    "nivel",
                    "codigo",
                    "mensagem",
                ]
            ].rename(
                columns={
                    "numero_proposta": "Nº PROPOSTA",
                    "proponente": "PROPONENTE",
                    "nivel": "NÍVEL",
                    "codigo": "CÓDIGO",
                    "mensagem": "MENSAGEM",
                }
            )
        )
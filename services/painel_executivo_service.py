from __future__ import annotations

import pandas as pd

from database import get_connection
from services.alerta_service import listar_alertas_gerais_df, listar_resumo_operacional_propostas, obter_resumo_alertas


def obter_painel_executivo() -> dict:
    resumo = listar_resumo_operacional_propostas()
    alertas_df = listar_alertas_gerais_df()
    resumo_alertas = obter_resumo_alertas()

    if resumo.empty:
        return {
            "metricas": {
                "total_propostas": 0,
                "total_autorizado": 0.0,
                "total_executado": 0.0,
                "total_pago": 0.0,
                "saldo_a_executar": 0.0,
                "saldo_a_pagar": 0.0,
                "propostas_sem_execucao": 0,
                "execucao_sem_pagamento": 0,
                "parcialmente_autorizadas": 0,
                "com_remanejamento": 0,
                "propostas_com_alerta": 0,
            },
            "status_df": pd.DataFrame(),
            "top_proponentes_df": pd.DataFrame(),
            "top_executores_df": pd.DataFrame(),
            "top_propostas_pagas_df": pd.DataFrame(),
            "top_saldo_pendente_df": pd.DataFrame(),
            "alertas_df": pd.DataFrame(),
            "resumo_alertas": resumo_alertas,
        }

    resumo = resumo.copy()
    resumo["saldo_a_executar"] = resumo["valor_autorizado_itens"] - resumo["valor_executado"]
    resumo["saldo_a_pagar"] = resumo["valor_executado"] - resumo["valor_pago"]

    metricas = {
        "total_propostas": int(len(resumo)),
        "total_autorizado": float(resumo["valor_autorizado_itens"].sum()),
        "total_executado": float(resumo["valor_executado"].sum()),
        "total_pago": float(resumo["valor_pago"].sum()),
        "saldo_a_executar": float(resumo["saldo_a_executar"].sum()),
        "saldo_a_pagar": float(resumo["saldo_a_pagar"].sum()),
        "propostas_sem_execucao": int(
            ((resumo["valor_autorizado_itens"] > 0) & (resumo["valor_executado"] <= 0) & (resumo["status"] != "REPROVADA")).sum()
        ),
        "execucao_sem_pagamento": int(((resumo["valor_executado"] > 0) & (resumo["valor_pago"] <= 0)).sum()),
        "parcialmente_autorizadas": int((resumo["status"] == "PARCIALMENTE AUTORIZADA").sum()),
        "com_remanejamento": int((resumo["total_remanejamentos"] > 0).sum()),
        "propostas_com_alerta": int(alertas_df["proposta_id"].nunique()) if not alertas_df.empty else 0,
    }

    status_df = (
        resumo.groupby("status", as_index=False)
        .agg(
            total_propostas=("proposta_id", "count"),
            valor_autorizado=("valor_autorizado_itens", "sum"),
            valor_executado=("valor_executado", "sum"),
            valor_pago=("valor_pago", "sum"),
        )
        .sort_values(by="total_propostas", ascending=False)
    )

    top_proponentes_df = (
        resumo.groupby("proponente", as_index=False)
        .agg(valor_autorizado=("valor_autorizado_itens", "sum"))
        .sort_values(by="valor_autorizado", ascending=False)
        .head(10)
    )

    top_propostas_pagas_df = (
        resumo[["numero_proposta", "proponente", "valor_pago"]]
        .sort_values(by="valor_pago", ascending=False)
        .head(10)
    )

    top_saldo_pendente_df = (
        resumo.assign(saldo_pendente=resumo["saldo_a_executar"] + resumo["saldo_a_pagar"])[
            ["numero_proposta", "proponente", "saldo_pendente"]
        ]
        .sort_values(by="saldo_pendente", ascending=False)
        .head(10)
    )

    conn = get_connection()
    try:
        top_executores_df = pd.read_sql_query(
            """
            SELECT
                COALESCE(ex.estabelecimento, x.cnes_executor, '-') AS executor,
                COALESCE(SUM(x.valor_total), 0) AS valor_executado
            FROM (
                SELECT executor_id, cnes_executor, valor_total
                FROM execucao_hospitalar
                UNION ALL
                SELECT executor_id, cnes_executor, valor_total
                FROM execucao_ambulatorial
            ) x
            LEFT JOIN executores ex ON ex.id = x.executor_id
            GROUP BY COALESCE(ex.estabelecimento, x.cnes_executor, '-')
            ORDER BY valor_executado DESC
            LIMIT 10
            """,
            conn,
        )
    finally:
        conn.close()

    if not alertas_df.empty:
        alertas_df = alertas_df.copy()
        prioridade = {"alto": 0, "medio": 1}
        alertas_df["ordem"] = alertas_df["nivel"].map(prioridade).fillna(9)
        alertas_df = (
            alertas_df.sort_values(by=["ordem", "numero_proposta", "codigo"])
            .drop(columns=["ordem"])
            .head(30)
        )

    return {
        "metricas": metricas,
        "status_df": status_df,
        "top_proponentes_df": top_proponentes_df,
        "top_executores_df": top_executores_df,
        "top_propostas_pagas_df": top_propostas_pagas_df,
        "top_saldo_pendente_df": top_saldo_pendente_df,
        "alertas_df": alertas_df,
        "resumo_alertas": resumo_alertas,
    }
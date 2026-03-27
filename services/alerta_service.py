from __future__ import annotations

import pandas as pd

from database import get_connection


def listar_resumo_operacional_propostas() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                p.id AS proposta_id,
                p.numero_proposta,
                COALESCE(p.proponente, '-') AS proponente,
                p.status,
                p.competencia_mes,
                p.competencia_ano,
                COALESCE(p.valor_total, 0) AS valor_total_proposta,
                COALESCE(p.valor_aprovado, 0) AS valor_aprovado_proposta,
                COALESCE((
                    SELECT SUM(pi.valor_autorizado)
                    FROM proposta_itens pi
                    WHERE pi.proposta_id = p.id
                ), 0) AS valor_autorizado_itens,
                COALESCE((
                    SELECT SUM(pi.quantidade_autorizada)
                    FROM proposta_itens pi
                    WHERE pi.proposta_id = p.id
                ), 0) AS qtd_autorizada_itens,
                COALESCE((
                    SELECT COUNT(*)
                    FROM proposta_itens pi
                    WHERE pi.proposta_id = p.id
                ), 0) AS qtd_itens,
                COALESCE((
                    SELECT COUNT(*)
                    FROM proposta_itens pi
                    WHERE pi.proposta_id = p.id
                      AND COALESCE(pi.quantidade_autorizada, 0) > 0
                ), 0) AS qtd_itens_autorizados,
                COALESCE((
                    SELECT SUM(valor_total)
                    FROM (
                        SELECT eh.valor_total
                        FROM execucao_hospitalar eh
                        WHERE eh.proposta_id = p.id
                        UNION ALL
                        SELECT ea.valor_total
                        FROM execucao_ambulatorial ea
                        WHERE ea.proposta_id = p.id
                    ) x
                ), 0) AS valor_executado,
                COALESCE((
                    SELECT SUM(valor_pago)
                    FROM pagamentos pag
                    WHERE pag.proposta_id = p.id
                ), 0) AS valor_pago,
                COALESCE((
                    SELECT COUNT(*)
                    FROM remanejamentos r
                    WHERE r.proposta_id = p.id
                ), 0) AS total_remanejamentos
            FROM propostas p
            ORDER BY p.id DESC
            """,
            conn,
        )
    finally:
        conn.close()


def avaliar_alertas_proposta(proposta_id: int) -> list[dict]:
    conn = get_connection()
    try:
        proposta = conn.execute(
            """
            SELECT
                p.id,
                p.numero_proposta,
                COALESCE(p.proponente, '-') AS proponente,
                COALESCE(p.status, '') AS status,
                COALESCE(p.valor_aprovado, 0) AS valor_aprovado_proposta
            FROM propostas p
            WHERE p.id = ?
            """,
            (proposta_id,),
        ).fetchone()

        if not proposta:
            return []

        row_sum = conn.execute(
            """
            SELECT
                COALESCE(SUM(pi.valor_autorizado), 0) AS valor_autorizado_itens,
                COALESCE(SUM(pi.quantidade_autorizada), 0) AS qtd_autorizada_itens,
                COALESCE(COUNT(*), 0) AS qtd_itens,
                COALESCE(SUM(
                    CASE WHEN COALESCE(pi.quantidade_autorizada, 0) > 0 THEN 1 ELSE 0 END
                ), 0) AS qtd_itens_autorizados
            FROM proposta_itens pi
            WHERE pi.proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        row_exec = conn.execute(
            """
            SELECT
                COALESCE(SUM(valor_total), 0) AS valor_executado
            FROM (
                SELECT eh.valor_total
                FROM execucao_hospitalar eh
                WHERE eh.proposta_id = ?
                UNION ALL
                SELECT ea.valor_total
                FROM execucao_ambulatorial ea
                WHERE ea.proposta_id = ?
            ) x
            """,
            (proposta_id, proposta_id),
        ).fetchone()

        row_pag = conn.execute(
            """
            SELECT COALESCE(SUM(valor_pago), 0) AS valor_pago
            FROM pagamentos
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        row_rem = conn.execute(
            """
            SELECT COALESCE(COUNT(*), 0) AS total_remanejamentos
            FROM remanejamentos
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        status = (proposta["status"] or "").strip().upper()
        valor_aprovado_proposta = float(proposta["valor_aprovado_proposta"] or 0)
        valor_autorizado_itens = float(row_sum["valor_autorizado_itens"] or 0)
        qtd_itens = int(row_sum["qtd_itens"] or 0)
        qtd_itens_autorizados = int(row_sum["qtd_itens_autorizados"] or 0)
        valor_executado = float(row_exec["valor_executado"] or 0)
        valor_pago = float(row_pag["valor_pago"] or 0)
        total_remanejamentos = int(row_rem["total_remanejamentos"] or 0)

        alertas: list[dict] = []

        def add(codigo: str, nivel: str, mensagem: str):
            alertas.append(
                {
                    "proposta_id": proposta_id,
                    "numero_proposta": proposta["numero_proposta"],
                    "proponente": proposta["proponente"],
                    "codigo": codigo,
                    "nivel": nivel,
                    "mensagem": mensagem,
                }
            )

        if status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA", "EM EXECUÇÃO", "PAGAMENTO PARCIAL", "PAGA"} and qtd_itens_autorizados <= 0:
            add("SEM_ITEM_AUTORIZADO", "alto", "Proposta em fase operacional sem item autorizado de fato.")

        if abs(valor_aprovado_proposta - valor_autorizado_itens) > 0.01:
            add("DIVERGENCIA_APROVADO", "alto", "Valor aprovado da proposta diverge da soma real dos itens autorizados.")

        if status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA"} and valor_executado <= 0 and valor_autorizado_itens > 0:
            add("AUTORIZADA_SEM_EXECUCAO", "medio", "Proposta autorizada sem execução registrada.")

        if valor_executado > 0 and valor_pago <= 0:
            add("EXECUCAO_SEM_PAGAMENTO", "medio", "Proposta com execução registrada e sem pagamento.")

        if valor_executado > 0 and valor_pago > 0 and (valor_pago / valor_executado) < 0.25:
            add("PAGAMENTO_MUITO_BAIXO", "medio", "Pagamento muito baixo em relação ao volume já executado.")

        if valor_pago - valor_executado > 0.01:
            add("PAGAMENTO_ACIMA_EXECUCAO", "alto", "Pagamento total acima da execução total.")

        if valor_autorizado_itens - valor_executado > 0 and valor_autorizado_itens > 0:
            saldo_exec = valor_autorizado_itens - valor_executado
            if (saldo_exec / valor_autorizado_itens) >= 0.70 and status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA"}:
                add("SALDO_ELEVADO_NAO_EXECUTADO", "medio", "Proposta com saldo elevado ainda não executado.")

        if status == "PAGA" and valor_pago < valor_executado:
            add("STATUS_INCOERENTE_PAGA", "alto", "Status PAGA incoerente com a movimentação financeira.")

        if status == "EM EXECUÇÃO" and valor_executado <= 0:
            add("STATUS_INCOERENTE_EXECUCAO", "medio", "Status EM EXECUÇÃO sem movimento de execução.")

        if total_remanejamentos > 0:
            row_crit = conn.execute(
                """
                SELECT COALESCE(MAX(
                    CASE
                        WHEN COALESCE(pi.quantidade_autorizada, 0) <= 0 THEN 0
                        ELSE (
                            (
                                COALESCE((
                                    SELECT SUM(eh.quantidade)
                                    FROM execucao_hospitalar eh
                                    WHERE eh.item_proposta_id = pi.id
                                ), 0)
                                +
                                COALESCE((
                                    SELECT SUM(ea.quantidade)
                                    FROM execucao_ambulatorial ea
                                    WHERE ea.item_proposta_id = pi.id
                                ), 0)
                            ) * 1.0 / pi.quantidade_autorizada
                        )
                    END
                ), 0) AS maior_comprometimento
                FROM proposta_itens pi
                WHERE pi.proposta_id = ?
                """,
                (proposta_id,),
            ).fetchone()

            maior_comp = float(row_crit["maior_comprometimento"] or 0)
            if maior_comp >= 0.90:
                add("REMANEJAMENTO_CRITICO", "medio", "Proposta com remanejamento e item altamente comprometido.")

        row_item_exec = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM proposta_itens pi
            WHERE pi.proposta_id = ?
              AND (
                    COALESCE((
                        SELECT SUM(eh.quantidade)
                        FROM execucao_hospitalar eh
                        WHERE eh.item_proposta_id = pi.id
                    ), 0)
                    +
                    COALESCE((
                        SELECT SUM(ea.quantidade)
                        FROM execucao_ambulatorial ea
                        WHERE ea.item_proposta_id = pi.id
                    ), 0)
                  ) > COALESCE(pi.quantidade_autorizada, 0)
            """,
            (proposta_id,),
        ).fetchone()

        if int(row_item_exec["total"] or 0) > 0:
            add("EXECUCAO_ACIMA_AUTORIZADO", "alto", "Há item com execução acima do autorizado.")

        row_item_pag = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM proposta_itens pi
            WHERE pi.proposta_id = ?
              AND COALESCE((
                    SELECT SUM(pag.valor_pago)
                    FROM pagamentos pag
                    WHERE pag.item_proposta_id = pi.id
                ), 0) >
                (
                    (
                        COALESCE((
                            SELECT SUM(eh.quantidade)
                            FROM execucao_hospitalar eh
                            WHERE eh.item_proposta_id = pi.id
                        ), 0)
                        +
                        COALESCE((
                            SELECT SUM(ea.quantidade)
                            FROM execucao_ambulatorial ea
                            WHERE ea.item_proposta_id = pi.id
                        ), 0)
                    ) * COALESCE(pi.valor_unitario, 0)
                )
            """,
            (proposta_id,),
        ).fetchone()

        if int(row_item_pag["total"] or 0) > 0:
            add("ITEM_PAGAMENTO_ACIMA_EXECUCAO", "alto", "Há item com pagamento acima da execução compatível.")

        if qtd_itens <= 0:
            add("SEM_ITENS", "medio", "Proposta sem itens cadastrados.")

        return alertas
    finally:
        conn.close()


def listar_alertas_proposta_df(proposta_id: int) -> pd.DataFrame:
    alertas = avaliar_alertas_proposta(proposta_id)
    if not alertas:
        return pd.DataFrame(columns=["codigo", "nivel", "mensagem"])
    return pd.DataFrame(alertas)


def listar_alertas_gerais_df() -> pd.DataFrame:
    resumo = listar_resumo_operacional_propostas()
    if resumo.empty:
        return pd.DataFrame(columns=["proposta_id", "numero_proposta", "proponente", "codigo", "nivel", "mensagem"])

    todos: list[dict] = []
    for proposta_id in resumo["proposta_id"].tolist():
        todos.extend(avaliar_alertas_proposta(int(proposta_id)))

    if not todos:
        return pd.DataFrame(columns=["proposta_id", "numero_proposta", "proponente", "codigo", "nivel", "mensagem"])

    return pd.DataFrame(todos)


def obter_resumo_alertas() -> dict:
    df = listar_alertas_gerais_df()
    if df.empty:
        return {
            "total_alertas": 0,
            "propostas_com_alerta": 0,
            "alertas_altos": 0,
            "alertas_medios": 0,
        }

    return {
        "total_alertas": int(len(df)),
        "propostas_com_alerta": int(df["proposta_id"].nunique()),
        "alertas_altos": int((df["nivel"] == "alto").sum()),
        "alertas_medios": int((df["nivel"] == "medio").sum()),
    }
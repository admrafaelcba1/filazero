from __future__ import annotations

from io import BytesIO

import pandas as pd

from database import get_connection


def _to_excel_bytes(dfs: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in dfs.items():
            nome = sheet_name[:31] if sheet_name else "Planilha"
            df.to_excel(writer, index=False, sheet_name=nome)
    output.seek(0)
    return output.getvalue()


def exportar_propostas_excel(
    competencia_ano: int | None = None,
    competencia_mes: int | None = None,
    status: str | None = None,
    proponente: str | None = None,
) -> bytes:
    conn = get_connection()
    try:
        query = """
            SELECT
                p.id,
                p.numero_proposta,
                p.proponente,
                p.ordem_proposta,
                p.competencia_mes,
                p.competencia_ano,
                p.quantidade_proposta,
                p.quantidade_proc_diversos,
                p.quantidade_cirurgia,
                p.valor_total,
                p.valor_aprovado,
                p.status,
                p.origem_recurso,
                p.deputado,
                p.parecer_tecnico,
                p.observacao,
                p.created_at
            FROM propostas p
            WHERE 1=1
        """
        params = []

        if competencia_ano:
            query += " AND p.competencia_ano = ?"
            params.append(competencia_ano)
        if competencia_mes:
            query += " AND p.competencia_mes = ?"
            params.append(competencia_mes)
        if status:
            query += " AND p.status = ?"
            params.append(status)
        if proponente:
            query += " AND p.proponente = ?"
            params.append(proponente)

        query += " ORDER BY p.id DESC"

        propostas = pd.read_sql_query(query, conn, params=params)

        itens = pd.read_sql_query(
            """
            SELECT
                pi.id,
                pi.proposta_id,
                p.numero_proposta,
                p.proponente,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                pi.classificacao,
                pi.subgrupo,
                pi.natureza,
                pi.quantidade,
                pi.quantidade_autorizada,
                pi.valor_unitario,
                pi.valor_total,
                pi.valor_autorizado
            FROM proposta_itens pi
            INNER JOIN propostas p ON p.id = pi.proposta_id
            ORDER BY pi.proposta_id, pi.id
            """,
            conn,
        )

        if not propostas.empty:
            propostas_ids = set(propostas["id"].tolist())
            itens = itens[itens["proposta_id"].isin(propostas_ids)].copy()

        return _to_excel_bytes(
            {
                "Propostas": propostas,
                "Itens_Proposta": itens,
            }
        )
    finally:
        conn.close()


def exportar_execucao_excel(proposta_id: int | None = None) -> bytes:
    conn = get_connection()
    try:
        q_hosp = """
            SELECT
                eh.id,
                eh.proposta_id,
                p.numero_proposta,
                p.proponente,
                'HOSPITALAR' AS tipo_execucao,
                eh.competencia_mes,
                eh.competencia_ano,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                eh.quantidade,
                eh.valor_total,
                eh.observacao,
                eh.created_at
            FROM execucao_hospitalar eh
            INNER JOIN proposta_itens pi ON pi.id = eh.item_proposta_id
            INNER JOIN propostas p ON p.id = eh.proposta_id
            WHERE 1=1
        """
        q_amb = """
            SELECT
                ea.id,
                ea.proposta_id,
                p.numero_proposta,
                p.proponente,
                'AMBULATORIAL' AS tipo_execucao,
                ea.competencia_mes,
                ea.competencia_ano,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                ea.quantidade,
                ea.valor_total,
                ea.observacao,
                ea.created_at
            FROM execucao_ambulatorial ea
            INNER JOIN proposta_itens pi ON pi.id = ea.item_proposta_id
            INNER JOIN propostas p ON p.id = ea.proposta_id
            WHERE 1=1
        """
        params = []
        if proposta_id:
            q_hosp += " AND eh.proposta_id = ?"
            q_amb += " AND ea.proposta_id = ?"
            params.append(proposta_id)

        df_hosp = pd.read_sql_query(q_hosp, conn, params=params)
        df_amb = pd.read_sql_query(q_amb, conn, params=params)

        consolidado = pd.concat([df_hosp, df_amb], ignore_index=True) if not (df_hosp.empty and df_amb.empty) else pd.DataFrame()

        return _to_excel_bytes(
            {
                "Execucao_Consolidada": consolidado,
                "Execucao_Hospitalar": df_hosp,
                "Execucao_Ambulatorial": df_amb,
            }
        )
    finally:
        conn.close()


def exportar_pagamentos_excel(proposta_id: int | None = None) -> bytes:
    conn = get_connection()
    try:
        query = """
            SELECT
                pag.id,
                pag.proposta_id,
                p.numero_proposta,
                p.proponente,
                pag.item_proposta_id,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                pag.tipo_execucao,
                pag.valor_pago,
                pag.observacao,
                pag.created_at
            FROM pagamentos pag
            INNER JOIN propostas p ON p.id = pag.proposta_id
            LEFT JOIN proposta_itens pi ON pi.id = pag.item_proposta_id
            WHERE 1=1
        """
        params = []
        if proposta_id:
            query += " AND pag.proposta_id = ?"
            params.append(proposta_id)
        query += " ORDER BY pag.id DESC"

        df = pd.read_sql_query(query, conn, params=params)
        return _to_excel_bytes({"Pagamentos": df})
    finally:
        conn.close()


def exportar_remanejamentos_excel(proposta_id: int | None = None) -> bytes:
    conn = get_connection()
    try:
        query = """
            SELECT
                r.id,
                r.proposta_id,
                p.numero_proposta,
                p.proponente,
                o.codigo_procedimento AS codigo_origem,
                o.descricao_procedimento AS descricao_origem,
                d.codigo_procedimento AS codigo_destino,
                d.descricao_procedimento AS descricao_destino,
                r.quantidade_origem_remanejada,
                r.valor_origem_remanejado,
                r.quantidade_destino_acrescida,
                r.valor_destino_acrescido,
                r.saldo_residual,
                r.justificativa,
                r.observacao,
                r.created_at
            FROM remanejamentos r
            INNER JOIN propostas p ON p.id = r.proposta_id
            INNER JOIN proposta_itens o ON o.id = r.item_origem_id
            INNER JOIN proposta_itens d ON d.id = r.item_destino_id
            WHERE 1=1
        """
        params = []
        if proposta_id:
            query += " AND r.proposta_id = ?"
            params.append(proposta_id)
        query += " ORDER BY r.id DESC"

        df = pd.read_sql_query(query, conn, params=params)
        return _to_excel_bytes({"Remanejamentos": df})
    finally:
        conn.close()
from __future__ import annotations

import pandas as pd

from database import get_connection
from services.auditoria_service import registrar_auditoria
from services.status_service import validar_pagamento_por_status
from services.status_automatico_service import atualizar_status_automatico_proposta


TIPOS_PAGAMENTO = ["HOSPITALAR", "AMBULATORIAL"]


def listar_propostas_para_pagamento() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                p.id,
                p.numero_proposta,
                COALESCE(p.proponente, '-') AS proponente_exibicao,
                p.competencia_mes,
                p.competencia_ano,
                p.status,
                p.valor_total,
                p.valor_aprovado
            FROM propostas p
            ORDER BY p.id DESC
            """,
            conn,
        )
    finally:
        conn.close()


def obter_resumo_proposta_pagamento(proposta_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                p.*,
                COALESCE(p.proponente, '-') AS proponente_exibicao
            FROM propostas p
            WHERE p.id = ?
            """,
            (proposta_id,),
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def listar_itens_com_saldo_pagamento(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT
                pi.id,
                pi.proposta_id,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                pi.classificacao,
                pi.subgrupo,
                pi.natureza,
                pi.quantidade,
                pi.quantidade_autorizada,
                pi.valor_unitario,
                pi.valor_total,
                pi.valor_autorizado,

                COALESCE((
                    SELECT SUM(eh.quantidade)
                    FROM execucao_hospitalar eh
                    WHERE eh.item_proposta_id = pi.id
                ), 0) AS qtd_exec_hospitalar,

                COALESCE((
                    SELECT SUM(ea.quantidade)
                    FROM execucao_ambulatorial ea
                    WHERE ea.item_proposta_id = pi.id
                ), 0) AS qtd_exec_ambulatorial,

                COALESCE((
                    SELECT SUM(pag.valor_pago)
                    FROM pagamentos pag
                    WHERE pag.item_proposta_id = pi.id
                      AND pag.tipo_execucao = 'HOSPITALAR'
                ), 0) AS valor_pago_hospitalar,

                COALESCE((
                    SELECT SUM(pag.valor_pago)
                    FROM pagamentos pag
                    WHERE pag.item_proposta_id = pi.id
                      AND pag.tipo_execucao = 'AMBULATORIAL'
                ), 0) AS valor_pago_ambulatorial

            FROM proposta_itens pi
            WHERE pi.proposta_id = ?
            ORDER BY pi.id
            """,
            conn,
            params=(proposta_id,),
        )

        if df.empty:
            return df

        df["valor_exec_hospitalar"] = df["qtd_exec_hospitalar"] * df["valor_unitario"].fillna(0)
        df["valor_exec_ambulatorial"] = df["qtd_exec_ambulatorial"] * df["valor_unitario"].fillna(0)
        df["valor_exec_total"] = df["valor_exec_hospitalar"] + df["valor_exec_ambulatorial"]
        df["valor_pago_total"] = df["valor_pago_hospitalar"] + df["valor_pago_ambulatorial"]
        df["saldo_pagamento_total"] = df["valor_exec_total"] - df["valor_pago_total"]
        df["saldo_pag_hospitalar"] = df["valor_exec_hospitalar"] - df["valor_pago_hospitalar"]
        df["saldo_pag_ambulatorial"] = df["valor_exec_ambulatorial"] - df["valor_pago_ambulatorial"]

        return df
    finally:
        conn.close()


def listar_pagamentos_proposta(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                pag.id,
                pag.proposta_id,
                pag.item_proposta_id,
                pag.executor_id,
                pag.cnes_executor,
                ex.estabelecimento AS executor_estabelecimento,
                pag.tipo_execucao,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                pag.valor_pago,
                pag.observacao,
                pag.created_at
            FROM pagamentos pag
            INNER JOIN proposta_itens pi ON pi.id = pag.item_proposta_id
            LEFT JOIN executores ex ON ex.id = pag.executor_id
            WHERE pag.proposta_id = ?
            ORDER BY pag.id DESC
            """,
            conn,
            params=(proposta_id,),
        )
    finally:
        conn.close()


def registrar_pagamento(
    proposta_id: int,
    item_proposta_id: int,
    tipo_execucao: str,
    valor_pago: float,
    executor_id: int,
    cnes_executor: str,
    observacao: str = "",
) -> tuple[bool, str]:
    ok_status, msg_status = validar_pagamento_por_status(proposta_id)
    if not ok_status:
        return False, msg_status

    if tipo_execucao not in TIPOS_PAGAMENTO:
        return False, "Tipo de pagamento inválido."

    if valor_pago <= 0:
        return False, "O valor pago deve ser maior que zero."

    conn = get_connection()
    pagamento_id = None
    codigo = ""
    descricao = ""
    try:
        item = conn.execute(
            """
            SELECT
                pi.id,
                pi.proposta_id,
                pi.valor_unitario,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                COALESCE((
                    SELECT SUM(eh.quantidade)
                    FROM execucao_hospitalar eh
                    WHERE eh.item_proposta_id = pi.id
                ), 0) AS qtd_exec_hospitalar,
                COALESCE((
                    SELECT SUM(ea.quantidade)
                    FROM execucao_ambulatorial ea
                    WHERE ea.item_proposta_id = pi.id
                ), 0) AS qtd_exec_ambulatorial,
                COALESCE((
                    SELECT SUM(pag.valor_pago)
                    FROM pagamentos pag
                    WHERE pag.item_proposta_id = pi.id
                      AND pag.tipo_execucao = 'HOSPITALAR'
                ), 0) AS valor_pago_hospitalar,
                COALESCE((
                    SELECT SUM(pag.valor_pago)
                    FROM pagamentos pag
                    WHERE pag.item_proposta_id = pi.id
                      AND pag.tipo_execucao = 'AMBULATORIAL'
                ), 0) AS valor_pago_ambulatorial
            FROM proposta_itens pi
            WHERE pi.id = ?
              AND pi.proposta_id = ?
            """,
            (item_proposta_id, proposta_id),
        ).fetchone()

        if not item:
            return False, "Item da proposta não encontrado."

        valor_unitario = float(item["valor_unitario"] or 0)

        valor_exec_hospitalar = float(item["qtd_exec_hospitalar"] or 0) * valor_unitario
        valor_exec_ambulatorial = float(item["qtd_exec_ambulatorial"] or 0) * valor_unitario

        valor_pago_hospitalar = float(item["valor_pago_hospitalar"] or 0)
        valor_pago_ambulatorial = float(item["valor_pago_ambulatorial"] or 0)

        if tipo_execucao == "HOSPITALAR":
            saldo = valor_exec_hospitalar - valor_pago_hospitalar
        else:
            saldo = valor_exec_ambulatorial - valor_pago_ambulatorial

        if saldo <= 0:
            return False, "Este item não possui saldo disponível para pagamento nesse tipo de execução."

        if valor_pago > saldo:
            return False, "O valor informado ultrapassa o saldo disponível para pagamento."

        cur = conn.execute(
            """
            INSERT INTO pagamentos (
                proposta_id,
                item_proposta_id,
                executor_id,
                cnes_executor,
                tipo_execucao,
                valor_pago,
                observacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposta_id,
                item_proposta_id,
                executor_id,
                cnes_executor,
                tipo_execucao,
                float(valor_pago),
                observacao.strip(),
            ),
        )
        pagamento_id = cur.lastrowid
        conn.commit()

        codigo = item["codigo_procedimento"]
        descricao = item["descricao_procedimento"]
    finally:
        conn.close()

    atualizar_status_automatico_proposta(proposta_id)
    registrar_auditoria(
        acao="REGISTRAR_PAGAMENTO",
        entidade="PAGAMENTO",
        entidade_id=pagamento_id,
        proposta_id=proposta_id,
        item_id=item_proposta_id,
        detalhes=(
            f"Tipo: {tipo_execucao} | Código: {codigo} | "
            f"Descrição: {descricao} | Valor pago: {float(valor_pago):.2f} | "
            f"Executor CNES: {cnes_executor}"
        ),
    )
    return True, "Pagamento registrado com sucesso."
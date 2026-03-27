from __future__ import annotations

import math
import pandas as pd

from database import get_connection
from services.auditoria_service import registrar_auditoria
from services.status_service import validar_remanejamento_por_status
from services.status_automatico_service import atualizar_status_automatico_proposta


def listar_propostas_para_remanejamento() -> pd.DataFrame:
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


def obter_resumo_proposta_remanejamento(proposta_id: int) -> dict | None:
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


def listar_itens_para_remanejamento(proposta_id: int) -> pd.DataFrame:
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
                ), 0) AS valor_pago_total
            FROM proposta_itens pi
            WHERE pi.proposta_id = ?
            ORDER BY pi.id
            """,
            conn,
            params=(proposta_id,),
        )

        if df.empty:
            return df

        df["qtd_executada_total"] = (
            df["qtd_exec_hospitalar"].fillna(0) + df["qtd_exec_ambulatorial"].fillna(0)
        )
        df["qtd_remanejavel"] = df["quantidade_autorizada"].fillna(0) - df["qtd_executada_total"]
        df["valor_remanejavel"] = df["qtd_remanejavel"] * df["valor_unitario"].fillna(0)

        df["grau_comprometimento"] = df.apply(
            lambda row: (
                0.0
                if float(row["quantidade_autorizada"] or 0) <= 0
                else (float(row["qtd_executada_total"] or 0) / float(row["quantidade_autorizada"] or 0))
            ),
            axis=1,
        )

        return df
    finally:
        conn.close()


def simular_remanejamento(
    proposta_id: int,
    item_origem_id: int,
    item_destino_id: int,
    quantidade_origem_remanejada: int,
) -> tuple[bool, str, dict | None]:
    ok_status, msg_status = validar_remanejamento_por_status(proposta_id)
    if not ok_status:
        return False, msg_status, None

    itens = listar_itens_para_remanejamento(proposta_id)
    if itens.empty:
        return False, "A proposta não possui itens para remanejamento.", None

    if item_origem_id == item_destino_id:
        return False, "Origem e destino não podem ser o mesmo item.", None

    origem_df = itens[itens["id"] == item_origem_id]
    destino_df = itens[itens["id"] == item_destino_id]

    if origem_df.empty:
        return False, "Item de origem não encontrado.", None
    if destino_df.empty:
        return False, "Item de destino não encontrado.", None

    origem = origem_df.iloc[0]
    destino = destino_df.iloc[0]

    qtd_remanejavel = int(origem["qtd_remanejavel"] or 0)
    if quantidade_origem_remanejada <= 0:
        return False, "A quantidade a remanejar deve ser maior que zero.", None

    if quantidade_origem_remanejada > qtd_remanejavel:
        return False, "A quantidade informada ultrapassa o saldo remanejável da origem.", None

    valor_origem = float(origem["valor_unitario"] or 0) * int(quantidade_origem_remanejada)
    valor_unitario_destino = float(destino["valor_unitario"] or 0)

    if valor_unitario_destino <= 0:
        return False, "O item de destino possui valor unitário inválido.", None

    quantidade_destino = int(math.floor(valor_origem / valor_unitario_destino))
    valor_destino = quantidade_destino * valor_unitario_destino
    saldo_residual = round(valor_origem - valor_destino, 2)

    origem_qtd_aut_atual = int(origem["quantidade_autorizada"] or 0)
    origem_qtd_exec = int(origem["qtd_executada_total"] or 0)
    destino_qtd_aut_atual = int(destino["quantidade_autorizada"] or 0)

    origem_qtd_aut_nova = origem_qtd_aut_atual - int(quantidade_origem_remanejada)
    destino_qtd_aut_nova = destino_qtd_aut_atual + int(quantidade_destino)

    alerta_pagamento = float(origem["valor_pago_total"] or 0) > 0
    alerta_comprometimento = float(origem["grau_comprometimento"] or 0) >= 0.8

    simulacao = {
        "origem": {
            "id": int(origem["id"]),
            "codigo": origem["codigo_procedimento"],
            "descricao": origem["descricao_procedimento"],
            "valor_unitario": float(origem["valor_unitario"] or 0),
            "quantidade_autorizada_atual": origem_qtd_aut_atual,
            "quantidade_executada": origem_qtd_exec,
            "qtd_remanejavel": qtd_remanejavel,
            "quantidade_autorizada_nova": origem_qtd_aut_nova,
            "valor_autorizado_atual": float(origem["valor_autorizado"] or 0),
            "valor_autorizado_novo": origem_qtd_aut_nova * float(origem["valor_unitario"] or 0),
            "valor_pago_total": float(origem["valor_pago_total"] or 0),
            "grau_comprometimento": float(origem["grau_comprometimento"] or 0),
        },
        "destino": {
            "id": int(destino["id"]),
            "codigo": destino["codigo_procedimento"],
            "descricao": destino["descricao_procedimento"],
            "valor_unitario": valor_unitario_destino,
            "quantidade_autorizada_atual": destino_qtd_aut_atual,
            "quantidade_autorizada_nova": destino_qtd_aut_nova,
            "valor_autorizado_atual": float(destino["valor_autorizado"] or 0),
            "valor_autorizado_novo": destino_qtd_aut_nova * valor_unitario_destino,
        },
        "movimento": {
            "quantidade_origem_remanejada": int(quantidade_origem_remanejada),
            "valor_origem_remanejado": round(valor_origem, 2),
            "quantidade_destino_acrescida": int(quantidade_destino),
            "valor_destino_acrescido": round(valor_destino, 2),
            "saldo_residual": round(saldo_residual, 2),
        },
        "alertas": {
            "possui_pagamento_origem": alerta_pagamento,
            "origem_muito_comprometida": alerta_comprometimento,
        },
    }

    if quantidade_destino <= 0:
        return (
            False,
            "O valor liberado na origem não é suficiente para acrescentar ao menos 1 unidade no destino.",
            simulacao,
        )

    if origem_qtd_aut_nova < origem_qtd_exec:
        return (
            False,
            "A simulação deixaria a origem com quantidade autorizada abaixo do que já foi executado.",
            simulacao,
        )

    if alerta_pagamento:
        return (
            True,
            "Simulação realizada com alerta: a origem já possui pagamento registrado. Revise com atenção antes de efetivar.",
            simulacao,
        )

    if alerta_comprometimento:
        return (
            True,
            "Simulação realizada com alerta: a origem está muito comprometida pela execução.",
            simulacao,
        )

    return True, "Simulação realizada com sucesso.", simulacao


def efetivar_remanejamento(
    proposta_id: int,
    item_origem_id: int,
    item_destino_id: int,
    quantidade_origem_remanejada: int,
    justificativa: str,
    observacao: str = "",
) -> tuple[bool, str]:
    ok_status, msg_status = validar_remanejamento_por_status(proposta_id)
    if not ok_status:
        return False, msg_status

    if not justificativa.strip():
        return False, "Informe a justificativa do remanejamento."

    ok, msg, simulacao = simular_remanejamento(
        proposta_id=proposta_id,
        item_origem_id=item_origem_id,
        item_destino_id=item_destino_id,
        quantidade_origem_remanejada=quantidade_origem_remanejada,
    )

    if not simulacao:
        return False, msg

    conn = get_connection()
    remanejamento_id = None
    try:
        origem = simulacao["origem"]
        destino = simulacao["destino"]
        movimento = simulacao["movimento"]

        nova_qtd_aut_origem = int(origem["quantidade_autorizada_nova"])
        nova_qtd_aut_destino = int(destino["quantidade_autorizada_nova"])

        if nova_qtd_aut_origem < int(origem["quantidade_executada"]):
            return False, "A origem não pode ficar com quantidade autorizada inferior ao que já foi executado."

        conn.execute(
            """
            UPDATE proposta_itens
            SET
                quantidade_autorizada = ?,
                valor_autorizado = ?
            WHERE id = ?
            """,
            (
                nova_qtd_aut_origem,
                nova_qtd_aut_origem * float(origem["valor_unitario"]),
                item_origem_id,
            ),
        )

        conn.execute(
            """
            UPDATE proposta_itens
            SET
                quantidade_autorizada = ?,
                valor_autorizado = ?
            WHERE id = ?
            """,
            (
                nova_qtd_aut_destino,
                nova_qtd_aut_destino * float(destino["valor_unitario"]),
                item_destino_id,
            ),
        )

        cur = conn.execute(
            """
            INSERT INTO remanejamentos (
                proposta_id,
                item_origem_id,
                item_destino_id,
                quantidade_origem_remanejada,
                valor_origem_remanejado,
                quantidade_destino_acrescida,
                valor_destino_acrescido,
                saldo_residual,
                justificativa,
                observacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposta_id,
                item_origem_id,
                item_destino_id,
                movimento["quantidade_origem_remanejada"],
                movimento["valor_origem_remanejado"],
                movimento["quantidade_destino_acrescida"],
                movimento["valor_destino_acrescido"],
                movimento["saldo_residual"],
                justificativa.strip(),
                observacao.strip(),
            ),
        )
        remanejamento_id = cur.lastrowid

        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(valor_autorizado), 0) AS total_autorizado,
                COALESCE(SUM(quantidade_autorizada), 0) AS total_qtd_aut
            FROM proposta_itens
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        conn.execute(
            """
            UPDATE propostas
            SET
                valor_aprovado = ?,
                quantidade_cirurgia = ?
            WHERE id = ?
            """,
            (
                float(row["total_autorizado"] or 0),
                int(row["total_qtd_aut"] or 0),
                proposta_id,
            ),
        )

        conn.commit()
    finally:
        conn.close()

    atualizar_status_automatico_proposta(proposta_id)
    registrar_auditoria(
        acao="EFETIVAR_REMANEJAMENTO",
        entidade="REMANEJAMENTO",
        entidade_id=remanejamento_id,
        proposta_id=proposta_id,
        item_id=item_origem_id,
        detalhes=(
            f"Origem: {origem['codigo']} | Destino: {destino['codigo']} | "
            f"Qtd origem remanejada: {movimento['quantidade_origem_remanejada']} | "
            f"Qtd destino acrescida: {movimento['quantidade_destino_acrescida']} | "
            f"Valor remanejado: {movimento['valor_origem_remanejado']:.2f} | "
            f"Saldo residual: {movimento['saldo_residual']:.2f} | "
            f"Justificativa: {justificativa.strip()}"
        ),
    )
    return True, "Remanejamento efetivado com sucesso."


def listar_historico_remanejamentos(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                r.id,
                r.created_at,
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
                r.observacao
            FROM remanejamentos r
            INNER JOIN proposta_itens o ON o.id = r.item_origem_id
            INNER JOIN proposta_itens d ON d.id = r.item_destino_id
            WHERE r.proposta_id = ?
            ORDER BY r.id DESC
            """,
            conn,
            params=(proposta_id,),
        )
    finally:
        conn.close()


def obter_resumo_geral_remanejamentos() -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_remanejamentos,
                COALESCE(SUM(valor_origem_remanejado), 0) AS total_valor_remanejado,
                COALESCE(SUM(saldo_residual), 0) AS total_saldo_residual
            FROM remanejamentos
            """
        ).fetchone()

        return {
            "total_remanejamentos": int(row["total_remanejamentos"] or 0),
            "total_valor_remanejado": float(row["total_valor_remanejado"] or 0),
            "total_saldo_residual": float(row["total_saldo_residual"] or 0),
        }
    finally:
        conn.close()
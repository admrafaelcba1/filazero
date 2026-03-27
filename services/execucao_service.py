from __future__ import annotations

import pandas as pd

from database import get_connection
from services.auditoria_service import registrar_auditoria
from services.status_service import validar_execucao_por_status
from services.status_automatico_service import atualizar_status_automatico_proposta


TIPOS_EXECUCAO = ["HOSPITALAR", "AMBULATORIAL"]


def listar_executores() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id,
                cnes,
                estabelecimento,
                municipio,
                estado
            FROM executores
            WHERE COALESCE(status, 'Ativo') = 'Ativo'
            ORDER BY estabelecimento
            """,
            conn,
        )
    finally:
        conn.close()


def listar_propostas_para_execucao() -> pd.DataFrame:
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


def obter_resumo_proposta_execucao(proposta_id: int) -> dict | None:
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


def listar_itens_autorizados_com_saldo(proposta_id: int) -> pd.DataFrame:
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
                ), 0) AS qtd_executada_hospitalar,
                COALESCE((
                    SELECT SUM(ea.quantidade)
                    FROM execucao_ambulatorial ea
                    WHERE ea.item_proposta_id = pi.id
                ), 0) AS qtd_executada_ambulatorial
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
            df["qtd_executada_hospitalar"].fillna(0) + df["qtd_executada_ambulatorial"].fillna(0)
        )
        df["saldo_quantidade"] = df["quantidade_autorizada"].fillna(0) - df["qtd_executada_total"]
        df["saldo_valor"] = df["saldo_quantidade"] * df["valor_unitario"].fillna(0)

        return df
    finally:
        conn.close()


def listar_execucoes_proposta(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        df_hosp = pd.read_sql_query(
            """
            SELECT
                eh.id,
                'HOSPITALAR' AS tipo_execucao,
                eh.competencia_mes,
                eh.competencia_ano,
                eh.item_proposta_id,
                eh.executor_id,
                eh.cnes_executor,
                ex.estabelecimento AS executor_estabelecimento,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                eh.quantidade,
                eh.valor_total,
                eh.observacao,
                eh.created_at
            FROM execucao_hospitalar eh
            INNER JOIN proposta_itens pi ON pi.id = eh.item_proposta_id
            LEFT JOIN executores ex ON ex.id = eh.executor_id
            WHERE eh.proposta_id = ?
            """,
            conn,
            params=(proposta_id,),
        )

        df_amb = pd.read_sql_query(
            """
            SELECT
                ea.id,
                'AMBULATORIAL' AS tipo_execucao,
                ea.competencia_mes,
                ea.competencia_ano,
                ea.item_proposta_id,
                ea.executor_id,
                ea.cnes_executor,
                ex.estabelecimento AS executor_estabelecimento,
                pi.codigo_procedimento,
                pi.descricao_procedimento,
                ea.quantidade,
                ea.valor_total,
                ea.observacao,
                ea.created_at
            FROM execucao_ambulatorial ea
            INNER JOIN proposta_itens pi ON pi.id = ea.item_proposta_id
            LEFT JOIN executores ex ON ex.id = ea.executor_id
            WHERE ea.proposta_id = ?
            """,
            conn,
            params=(proposta_id,),
        )

        if df_hosp.empty and df_amb.empty:
            return pd.DataFrame()

        return pd.concat([df_hosp, df_amb], ignore_index=True).sort_values(
            by=["competencia_ano", "competencia_mes", "id"],
            ascending=[False, False, False],
        )
    finally:
        conn.close()


def registrar_execucao(
    proposta_id: int,
    item_proposta_id: int,
    tipo_execucao: str,
    competencia_mes: int,
    competencia_ano: int,
    quantidade: int,
    executor_id: int,
    cnes_executor: str,
    observacao: str = "",
) -> tuple[bool, str]:
    ok_status, msg_status = validar_execucao_por_status(proposta_id)
    if not ok_status:
        return False, msg_status

    if tipo_execucao not in TIPOS_EXECUCAO:
        return False, "Tipo de execução inválido."

    if quantidade <= 0:
        return False, "A quantidade executada deve ser maior que zero."

    conn = get_connection()
    execucao_id = None
    valor_total = 0.0
    try:
        item = conn.execute(
            """
            SELECT
                id,
                proposta_id,
                quantidade_autorizada,
                valor_unitario,
                codigo_procedimento,
                descricao_procedimento
            FROM proposta_itens
            WHERE id = ? AND proposta_id = ?
            """,
            (item_proposta_id, proposta_id),
        ).fetchone()

        if not item:
            return False, "Item da proposta não encontrado."

        qtd_hosp = conn.execute(
            """
            SELECT COALESCE(SUM(quantidade), 0) AS total
            FROM execucao_hospitalar
            WHERE item_proposta_id = ?
            """,
            (item_proposta_id,),
        ).fetchone()["total"]

        qtd_amb = conn.execute(
            """
            SELECT COALESCE(SUM(quantidade), 0) AS total
            FROM execucao_ambulatorial
            WHERE item_proposta_id = ?
            """,
            (item_proposta_id,),
        ).fetchone()["total"]

        qtd_ja_executada = int(qtd_hosp or 0) + int(qtd_amb or 0)
        qtd_autorizada = int(item["quantidade_autorizada"] or 0)
        saldo = qtd_autorizada - qtd_ja_executada

        if saldo <= 0:
            return False, "Este item não possui saldo de execução."

        if quantidade > saldo:
            return False, "A quantidade informada ultrapassa o saldo autorizado para execução."

        valor_unitario = float(item["valor_unitario"] or 0)
        valor_total = quantidade * valor_unitario

        tabela = "execucao_hospitalar" if tipo_execucao == "HOSPITALAR" else "execucao_ambulatorial"

        cur = conn.execute(
            f"""
            INSERT INTO {tabela} (
                proposta_id,
                item_proposta_id,
                executor_id,
                cnes_executor,
                competencia_mes,
                competencia_ano,
                quantidade,
                valor_total,
                observacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposta_id,
                item_proposta_id,
                executor_id,
                cnes_executor,
                competencia_mes,
                competencia_ano,
                quantidade,
                valor_total,
                observacao.strip(),
            ),
        )
        execucao_id = cur.lastrowid

        conn.commit()

        codigo = item["codigo_procedimento"]
        descricao = item["descricao_procedimento"]
    finally:
        conn.close()

    atualizar_status_automatico_proposta(proposta_id)
    registrar_auditoria(
        acao="REGISTRAR_EXECUCAO",
        entidade="EXECUCAO",
        entidade_id=execucao_id,
        proposta_id=proposta_id,
        item_id=item_proposta_id,
        detalhes=(
            f"Tipo: {tipo_execucao} | Código: {codigo} | "
            f"Descrição: {descricao} | Quantidade: {quantidade} | "
            f"Valor total: {valor_total:.2f} | Executor CNES: {cnes_executor} | "
            f"Competência: {competencia_mes}/{competencia_ano}"
        ),
    )
    return True, "Execução registrada com sucesso."
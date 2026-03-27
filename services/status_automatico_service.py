from database import get_connection


def atualizar_status_automatico_proposta(proposta_id: int) -> None:
    conn = get_connection()
    try:
        proposta = conn.execute(
            """
            SELECT id, status
            FROM propostas
            WHERE id = ?
            """,
            (proposta_id,),
        ).fetchone()

        if not proposta:
            return

        status_atual = (proposta["status"] or "").strip().upper()

        if status_atual == "REPROVADA":
            return

        row_base = conn.execute(
            """
            SELECT
                COALESCE(SUM(quantidade), 0) AS qtd_proposta,
                COALESCE(SUM(quantidade_autorizada), 0) AS qtd_autorizada,
                COALESCE(SUM(valor_autorizado), 0) AS valor_autorizado
            FROM proposta_itens
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        qtd_proposta = int(row_base["qtd_proposta"] or 0)
        qtd_autorizada = int(row_base["qtd_autorizada"] or 0)
        valor_autorizado = float(row_base["valor_autorizado"] or 0)

        row_exec = conn.execute(
            """
            SELECT COALESCE(SUM(valor_total), 0) AS valor_exec
            FROM (
                SELECT valor_total FROM execucao_hospitalar WHERE proposta_id = ?
                UNION ALL
                SELECT valor_total FROM execucao_ambulatorial WHERE proposta_id = ?
            ) x
            """,
            (proposta_id, proposta_id),
        ).fetchone()

        valor_executado = float(row_exec["valor_exec"] or 0)

        row_pag = conn.execute(
            """
            SELECT COALESCE(SUM(valor_pago), 0) AS valor_pago
            FROM pagamentos
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        valor_pago = float(row_pag["valor_pago"] or 0)

        if qtd_proposta <= 0:
            novo_status = "EM ELABORACAO"
        elif qtd_autorizada <= 0:
            if status_atual == "EM ANALISE":
                novo_status = "EM ANALISE"
            else:
                novo_status = "EM ELABORACAO"
        elif qtd_autorizada < qtd_proposta:
            if valor_executado <= 0:
                novo_status = "PARCIALMENTE AUTORIZADA"
            elif valor_pago <= 0:
                novo_status = "EM EXECUÇÃO"
            elif valor_pago < valor_executado:
                novo_status = "PAGAMENTO PARCIAL"
            else:
                novo_status = "PAGA"
        else:
            if valor_executado <= 0:
                novo_status = "AUTORIZADA"
            elif valor_pago <= 0:
                novo_status = "EM EXECUÇÃO"
            elif valor_pago < valor_executado:
                novo_status = "PAGAMENTO PARCIAL"
            else:
                novo_status = "PAGA"

        if valor_executado <= 0 and novo_status == "PAGA":
            novo_status = "AUTORIZADA" if valor_autorizado > 0 else "EM ELABORACAO"

        conn.execute(
            """
            UPDATE propostas
            SET status = ?
            WHERE id = ?
            """,
            (novo_status, proposta_id),
        )
        conn.commit()
    finally:
        conn.close()
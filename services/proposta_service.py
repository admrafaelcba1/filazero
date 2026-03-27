from __future__ import annotations

import re
import pandas as pd

from database import get_connection
from services.auditoria_service import registrar_auditoria
from services.fase_service import validar_alteracao_estrutural_proposta, validar_autorizacao_proposta
from services.status_automatico_service import atualizar_status_automatico_proposta


STATUS_PROPOSTA = [
    "EM ELABORACAO",
    "EM ANALISE",
    "PARCIALMENTE AUTORIZADA",
    "AUTORIZADA",
    "EM EXECUÇÃO",
    "PAGAMENTO PARCIAL",
    "PAGA",
    "REPROVADA",
]

ORIGENS_RECURSO_PADRAO = [
    "EMENDA PARLAMENTAR",
    "RECURSO PRÓPRIO",
    "RECURSO FEDERAL",
    "RECURSO ESTADUAL",
    "OUTRO",
]


def listar_proponentes_opcoes() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT id, proponente, ibge, cnes, cnpj_fms, nome_completo
            FROM proponentes
            WHERE COALESCE(status, 'Ativo') = 'Ativo'
            ORDER BY proponente
            """,
            conn,
        )
    finally:
        conn.close()


def gerar_numero_proposta_automatico(ano: int) -> str:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT numero_proposta
            FROM propostas
            WHERE numero_proposta LIKE ?
            ORDER BY id DESC
            """,
            (f"%/{ano}/FILAZERO",),
        ).fetchall()

        maior = 0
        for row in rows:
            numero = row["numero_proposta"] or ""
            match = re.match(r"^(\d{3})/" + str(ano) + r"/FILAZERO$", numero)
            if match:
                maior = max(maior, int(match.group(1)))

        proximo = maior + 1
        return f"{proximo:03d}/{ano}/FILAZERO"
    finally:
        conn.close()


def buscar_catalogo_para_select(filtro: str = "") -> pd.DataFrame:
    conn = get_connection()
    try:
        if filtro.strip():
            termo = f"%{filtro.strip()}%"
            return pd.read_sql_query(
                """
                SELECT
                    codigo_sigtap AS codigo,
                    descricao_procedimento AS descricao,
                    valor_unitario,
                    classificacao,
                    subgrupo_descricao AS subgrupo,
                    COALESCE(
                        natureza,
                        CASE
                            WHEN UPPER(COALESCE(classificacao, '')) = 'AMB' THEN 'AMB'
                            WHEN UPPER(COALESCE(classificacao, '')) = 'AMB/HOSP' THEN 'AMB/HOSP'
                            ELSE 'HOSP'
                        END
                    ) AS natureza
                FROM catalogo_procedimentos
                WHERE codigo_sigtap LIKE ?
                   OR descricao_procedimento LIKE ?
                ORDER BY descricao_procedimento
                """,
                conn,
                params=(termo, termo),
            )

        return pd.read_sql_query(
            """
            SELECT
                codigo_sigtap AS codigo,
                descricao_procedimento AS descricao,
                valor_unitario,
                classificacao,
                subgrupo_descricao AS subgrupo,
                COALESCE(
                    natureza,
                    CASE
                        WHEN UPPER(COALESCE(classificacao, '')) = 'AMB' THEN 'AMB'
                        WHEN UPPER(COALESCE(classificacao, '')) = 'AMB/HOSP' THEN 'AMB/HOSP'
                        ELSE 'HOSP'
                    END
                ) AS natureza
            FROM catalogo_procedimentos
            ORDER BY descricao_procedimento
            LIMIT 500
            """,
            conn,
        )
    finally:
        conn.close()


def obter_catalogo_por_codigo(codigo: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                codigo_sigtap AS codigo,
                descricao_procedimento AS descricao,
                valor_unitario,
                classificacao,
                subgrupo_descricao AS subgrupo,
                COALESCE(
                    natureza,
                    CASE
                        WHEN UPPER(COALESCE(classificacao, '')) = 'AMB' THEN 'AMB'
                        WHEN UPPER(COALESCE(classificacao, '')) = 'AMB/HOSP' THEN 'AMB/HOSP'
                        ELSE 'HOSP'
                    END
                ) AS natureza
            FROM catalogo_procedimentos
            WHERE codigo_sigtap = ?
            """,
            (codigo,),
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def criar_proposta(
    numero_proposta: str,
    proponente_id: int | None,
    proponente: str,
    ordem_proposta: int,
    competencia_mes: int,
    competencia_ano: int,
    origem_recurso: str,
    deputado: str,
    status: str,
    observacao: str,
) -> tuple[bool, str, int | None]:
    if not numero_proposta.strip():
        return False, "Informe o Nº da proposta.", None

    if not proponente.strip():
        return False, "Informe o PROPONENTE.", None

    if status not in STATUS_PROPOSTA:
        return False, "Status inválido.", None

    conn = get_connection()
    try:
        existe = conn.execute(
            "SELECT id FROM propostas WHERE numero_proposta = ?",
            (numero_proposta.strip(),),
        ).fetchone()

        if existe:
            return False, "Já existe uma proposta com esse número.", None

        cur = conn.execute(
            """
            INSERT INTO propostas (
                numero_proposta,
                proponente_id,
                proponente,
                ordem_proposta,
                competencia_mes,
                competencia_ano,
                origem_recurso,
                deputado,
                status,
                observacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                numero_proposta.strip(),
                proponente_id,
                proponente.strip(),
                int(ordem_proposta),
                int(competencia_mes),
                int(competencia_ano),
                origem_recurso.strip(),
                deputado.strip(),
                status,
                observacao.strip(),
            ),
        )
        proposta_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    registrar_auditoria(
        acao="CRIAR",
        entidade="PROPOSTA",
        entidade_id=proposta_id,
        proposta_id=proposta_id,
        detalhes=f"Proposta criada. Número: {numero_proposta.strip()} | Proponente: {proponente.strip()} | Competência: {competencia_mes}/{competencia_ano} | Status inicial: {status}",
    )
    return True, "Proposta criada com sucesso.", proposta_id


def listar_propostas() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                p.id,
                p.numero_proposta,
                p.proponente,
                p.ordem_proposta,
                p.competencia_mes,
                p.competencia_ano,
                p.origem_recurso,
                p.deputado,
                p.status,
                p.quantidade_proposta,
                p.quantidade_proc_diversos,
                p.quantidade_cirurgia,
                p.valor_total,
                p.valor_aprovado
            FROM propostas p
            ORDER BY p.id DESC
            """,
            conn,
        )
    finally:
        conn.close()


def obter_proposta(proposta_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT p.*
            FROM propostas p
            WHERE p.id = ?
            """,
            (proposta_id,),
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def listar_itens_da_proposta(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id,
                codigo_procedimento,
                descricao_procedimento,
                classificacao,
                subgrupo,
                natureza,
                quantidade,
                quantidade_autorizada,
                valor_unitario,
                valor_total,
                valor_autorizado
            FROM proposta_itens
            WHERE proposta_id = ?
            ORDER BY id
            """,
            conn,
            params=(proposta_id,),
        )
    finally:
        conn.close()


def _obter_uso_operacional_item(conn, item_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            COALESCE((
                SELECT SUM(quantidade)
                FROM execucao_hospitalar
                WHERE item_proposta_id = ?
            ), 0) AS qtd_exec_hospitalar,
            COALESCE((
                SELECT SUM(quantidade)
                FROM execucao_ambulatorial
                WHERE item_proposta_id = ?
            ), 0) AS qtd_exec_ambulatorial,
            COALESCE((
                SELECT SUM(valor_pago)
                FROM pagamentos
                WHERE item_proposta_id = ?
            ), 0) AS valor_pago_total
        """,
        (item_id, item_id, item_id),
    ).fetchone()

    qtd_exec_hospitalar = int(row["qtd_exec_hospitalar"] or 0)
    qtd_exec_ambulatorial = int(row["qtd_exec_ambulatorial"] or 0)
    qtd_exec_total = qtd_exec_hospitalar + qtd_exec_ambulatorial
    valor_pago_total = float(row["valor_pago_total"] or 0)

    return {
        "qtd_exec_hospitalar": qtd_exec_hospitalar,
        "qtd_exec_ambulatorial": qtd_exec_ambulatorial,
        "qtd_exec_total": qtd_exec_total,
        "valor_pago_total": valor_pago_total,
        "possui_execucao": qtd_exec_total > 0,
        "possui_pagamento": valor_pago_total > 0,
    }


def adicionar_item_proposta(
    proposta_id: int,
    codigo_procedimento: str,
    quantidade: int,
) -> tuple[bool, str]:
    ok_fase, msg_fase = validar_alteracao_estrutural_proposta(proposta_id)
    if not ok_fase:
        return False, msg_fase

    if quantidade <= 0:
        return False, "A quantidade deve ser maior que zero."

    catalogo = obter_catalogo_por_codigo(codigo_procedimento)
    if not catalogo:
        return False, "Procedimento não encontrado no catálogo."

    valor_unitario = float(catalogo["valor_unitario"] or 0)

    conn = get_connection()
    item_id = None
    try:
        existente = conn.execute(
            """
            SELECT id, quantidade
            FROM proposta_itens
            WHERE proposta_id = ? AND codigo_procedimento = ?
            """,
            (proposta_id, codigo_procedimento),
        ).fetchone()

        if existente:
            item_id = int(existente["id"])
            quantidade_anterior = int(existente["quantidade"] or 0)
            nova_quantidade = quantidade_anterior + quantidade
            novo_valor_total = nova_quantidade * valor_unitario
            conn.execute(
                """
                UPDATE proposta_itens
                SET
                    quantidade = ?,
                    valor_unitario = ?,
                    valor_total = ?,
                    descricao_procedimento = ?,
                    classificacao = ?,
                    subgrupo = ?,
                    natureza = ?
                WHERE id = ?
                """,
                (
                    nova_quantidade,
                    valor_unitario,
                    novo_valor_total,
                    catalogo["descricao"],
                    catalogo["classificacao"],
                    catalogo["subgrupo"],
                    catalogo["natureza"],
                    item_id,
                ),
            )
            detalhes = f"Quantidade acrescida no item existente. Código: {codigo_procedimento} | Quantidade anterior: {quantidade_anterior} | Quantidade adicionada: {quantidade} | Nova quantidade: {nova_quantidade}"
        else:
            cur = conn.execute(
                """
                INSERT INTO proposta_itens (
                    proposta_id,
                    codigo_procedimento,
                    descricao_procedimento,
                    quantidade,
                    quantidade_autorizada,
                    valor_unitario,
                    valor_total,
                    valor_autorizado,
                    classificacao,
                    subgrupo,
                    natureza
                )
                VALUES (?, ?, ?, ?, 0, ?, ?, 0, ?, ?, ?)
                """,
                (
                    proposta_id,
                    codigo_procedimento,
                    catalogo["descricao"],
                    quantidade,
                    valor_unitario,
                    quantidade * valor_unitario,
                    catalogo["classificacao"],
                    catalogo["subgrupo"],
                    catalogo["natureza"],
                ),
            )
            item_id = cur.lastrowid
            detalhes = f"Item incluído na proposta. Código: {codigo_procedimento} | Descrição: {catalogo['descricao']} | Quantidade: {quantidade} | Valor unitário: {valor_unitario:.2f}"

        recalcular_totais_proposta(proposta_id, conn=conn)
        conn.commit()
    finally:
        conn.close()

    atualizar_status_automatico_proposta(proposta_id)
    registrar_auditoria(
        acao="ADICIONAR_ITEM",
        entidade="PROPOSTA_ITEM",
        entidade_id=item_id,
        proposta_id=proposta_id,
        item_id=item_id,
        detalhes=detalhes,
    )
    return True, "Item adicionado com sucesso."


def autorizar_item(item_id: int, quantidade_autorizada: int) -> tuple[bool, str]:
    conn = get_connection()
    proposta_id = None
    detalhes = ""
    try:
        item = conn.execute(
            """
            SELECT id, proposta_id, quantidade, valor_unitario, quantidade_autorizada
            FROM proposta_itens
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

        if not item:
            return False, "Item não encontrado."

        proposta_id = int(item["proposta_id"])

        ok_fase, msg_fase = validar_autorizacao_proposta(proposta_id)
        if not ok_fase:
            return False, msg_fase

        quantidade = int(item["quantidade"] or 0)
        quantidade_autorizada_anterior = int(item["quantidade_autorizada"] or 0)

        if quantidade_autorizada < 0:
            return False, "A quantidade autorizada não pode ser negativa."

        if quantidade_autorizada > quantidade:
            return False, "A quantidade autorizada não pode ser maior que a quantidade proposta."

        uso = _obter_uso_operacional_item(conn, item_id)
        qtd_executada = int(uso["qtd_exec_total"])

        if quantidade_autorizada < qtd_executada:
            return False, f"Não é permitido autorizar quantidade inferior ao que já foi executado neste item ({qtd_executada})."

        valor_unitario = float(item["valor_unitario"] or 0)
        valor_autorizado = quantidade_autorizada * valor_unitario

        conn.execute(
            """
            UPDATE proposta_itens
            SET quantidade_autorizada = ?, valor_autorizado = ?
            WHERE id = ?
            """,
            (quantidade_autorizada, valor_autorizado, item_id),
        )

        recalcular_totais_proposta(proposta_id, conn=conn)
        conn.commit()

        detalhes = (
            f"Autorização alterada no item. Quantidade autorizada anterior: {quantidade_autorizada_anterior} | "
            f"Nova quantidade autorizada: {quantidade_autorizada} | Quantidade já executada: {qtd_executada}"
        )
    finally:
        conn.close()

    if proposta_id is not None:
        atualizar_status_automatico_proposta(proposta_id)
        registrar_auditoria(
            acao="AUTORIZAR_ITEM",
            entidade="PROPOSTA_ITEM",
            entidade_id=item_id,
            proposta_id=proposta_id,
            item_id=item_id,
            detalhes=detalhes,
        )
    return True, "Autorização atualizada com sucesso."


def excluir_item(item_id: int) -> tuple[bool, str]:
    conn = get_connection()
    proposta_id = None
    detalhes = ""
    try:
        row = conn.execute(
            """
            SELECT id, proposta_id, codigo_procedimento, descricao_procedimento, quantidade
            FROM proposta_itens
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

        if not row:
            return False, "Item não encontrado."

        proposta_id = int(row["proposta_id"])

        ok_fase, msg_fase = validar_alteracao_estrutural_proposta(proposta_id)
        if not ok_fase:
            return False, msg_fase

        uso = _obter_uso_operacional_item(conn, item_id)
        if uso["possui_execucao"]:
            return False, "Não é permitido excluir item que já possui execução registrada."

        if uso["possui_pagamento"]:
            return False, "Não é permitido excluir item que já possui pagamento registrado."

        detalhes = (
            f"Item excluído da proposta. Código: {row['codigo_procedimento']} | "
            f"Descrição: {row['descricao_procedimento']} | Quantidade proposta: {int(row['quantidade'] or 0)}"
        )

        conn.execute("DELETE FROM proposta_itens WHERE id = ?", (item_id,))
        recalcular_totais_proposta(proposta_id, conn=conn)
        conn.commit()
    finally:
        conn.close()

    if proposta_id is not None:
        atualizar_status_automatico_proposta(proposta_id)
        registrar_auditoria(
            acao="EXCLUIR_ITEM",
            entidade="PROPOSTA_ITEM",
            entidade_id=item_id,
            proposta_id=proposta_id,
            item_id=item_id,
            detalhes=detalhes,
        )
    return True, "Item excluído com sucesso."


def atualizar_status_proposta(proposta_id: int, status: str, parecer_tecnico: str) -> tuple[bool, str]:
    if status not in STATUS_PROPOSTA:
        return False, "Status inválido."

    conn = get_connection()
    try:
        atual = conn.execute(
            "SELECT status FROM propostas WHERE id = ?",
            (proposta_id,),
        ).fetchone()
        status_anterior = (atual["status"] or "").strip() if atual else ""

        conn.execute(
            """
            UPDATE propostas
            SET status = ?, parecer_tecnico = ?
            WHERE id = ?
            """,
            (status, parecer_tecnico.strip(), proposta_id),
        )
        conn.commit()
    finally:
        conn.close()

    registrar_auditoria(
        acao="ATUALIZAR_STATUS",
        entidade="PROPOSTA",
        entidade_id=proposta_id,
        proposta_id=proposta_id,
        detalhes=f"Status alterado manualmente. Anterior: {status_anterior} | Novo: {status} | Parecer: {parecer_tecnico.strip()}",
    )
    return True, "Status da proposta atualizado com sucesso."


def recalcular_totais_proposta(proposta_id: int, conn=None):
    fechar = False
    if conn is None:
        conn = get_connection()
        fechar = True

    try:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(quantidade), 0) AS qtd_total,
                COALESCE(SUM(valor_total), 0) AS valor_total,
                COALESCE(SUM(quantidade_autorizada), 0) AS qtd_aut,
                COALESCE(SUM(valor_autorizado), 0) AS valor_aut
            FROM proposta_itens
            WHERE proposta_id = ?
            """,
            (proposta_id,),
        ).fetchone()

        qtd_total = int(row["qtd_total"] or 0)
        valor_total = float(row["valor_total"] or 0)
        qtd_aut = int(row["qtd_aut"] or 0)
        valor_aut = float(row["valor_aut"] or 0)

        conn.execute(
            """
            UPDATE propostas
            SET
                quantidade_proposta = ?,
                quantidade_proc_diversos = ?,
                quantidade_cirurgia = ?,
                valor_total = ?,
                valor_aprovado = ?
            WHERE id = ?
            """,
            (
                qtd_total,
                0,
                qtd_aut,
                valor_total,
                valor_aut,
                proposta_id,
            ),
        )

        if fechar:
            conn.commit()
    finally:
        if fechar:
            conn.close()
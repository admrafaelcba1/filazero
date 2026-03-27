from __future__ import annotations

from database import get_connection


FASES_PROPOSTA = [
    "EM ELABORACAO",
    "EM ANALISE",
    "PARCIALMENTE AUTORIZADA",
    "AUTORIZADA",
    "EM EXECUÇÃO",
    "PAGAMENTO PARCIAL",
    "PAGA",
    "REPROVADA",
]


def _normalizar_status(status: str | None) -> str:
    return (status or "").strip().upper()


def obter_status_proposta(proposta_id: int) -> str | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM propostas WHERE id = ?",
            (proposta_id,),
        ).fetchone()
        return _normalizar_status(row["status"]) if row else None
    finally:
        conn.close()


def obter_contexto_fase_proposta(proposta_id: int) -> dict:
    status = obter_status_proposta(proposta_id)

    if not status:
        return {
            "status": None,
            "pode_adicionar_item": False,
            "pode_excluir_item": False,
            "pode_autorizar_item": False,
            "pode_executar": False,
            "pode_pagar": False,
            "pode_remanejar": False,
            "mensagem_edicao": "Proposta não encontrada.",
            "mensagem_execucao": "Proposta não encontrada.",
            "mensagem_pagamento": "Proposta não encontrada.",
            "mensagem_remanejamento": "Proposta não encontrada.",
        }

    pode_adicionar_item = status in {"EM ELABORACAO", "EM ANALISE"}
    pode_excluir_item = status in {"EM ELABORACAO", "EM ANALISE"}
    pode_autorizar_item = status in {
        "EM ELABORACAO",
        "EM ANALISE",
        "PARCIALMENTE AUTORIZADA",
        "AUTORIZADA",
    }
    pode_executar = status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA", "EM EXECUÇÃO"}
    pode_pagar = status in {
        "PARCIALMENTE AUTORIZADA",
        "AUTORIZADA",
        "EM EXECUÇÃO",
        "PAGAMENTO PARCIAL",
    }
    pode_remanejar = status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA"}

    def _msg_edicao() -> str:
        if status == "REPROVADA":
            return "Proposta reprovada: edição estrutural bloqueada."
        if status == "PAGA":
            return "Proposta paga: edição estrutural bloqueada."
        if status == "PAGAMENTO PARCIAL":
            return "Pagamento parcial em andamento: estrutura da proposta bloqueada."
        if status == "EM EXECUÇÃO":
            return "Proposta em execução: edição estrutural bloqueada."
        if status in {"PARCIALMENTE AUTORIZADA", "AUTORIZADA"}:
            return "Proposta autorizada: inclusão/exclusão estrutural bloqueada."
        return ""

    def _msg_execucao() -> str:
        if status == "REPROVADA":
            return "Execução não permitida: proposta reprovada."
        if status in {"EM ELABORACAO", "EM ANALISE"}:
            return f"Execução não permitida para a fase atual: {status}."
        if status == "PAGA":
            return "Execução não permitida: proposta já paga."
        if status == "PAGAMENTO PARCIAL":
            return "Execução não permitida: proposta em pagamento parcial."
        return ""

    def _msg_pagamento() -> str:
        if status == "REPROVADA":
            return "Pagamento não permitido: proposta reprovada."
        if status in {"EM ELABORACAO", "EM ANALISE"}:
            return f"Pagamento não permitido para a fase atual: {status}."
        if status == "PAGA":
            return "Pagamento não permitido: proposta já paga."
        return ""

    def _msg_remanejamento() -> str:
        if status == "REPROVADA":
            return "Remanejamento não permitido: proposta reprovada."
        if status in {"EM ELABORACAO", "EM ANALISE"}:
            return f"Remanejamento não permitido para a fase atual: {status}."
        if status == "EM EXECUÇÃO":
            return "Remanejamento bloqueado: proposta já está em execução."
        if status == "PAGAMENTO PARCIAL":
            return "Remanejamento bloqueado: proposta está em pagamento parcial."
        if status == "PAGA":
            return "Remanejamento bloqueado: proposta já paga."
        return ""

    return {
        "status": status,
        "pode_adicionar_item": pode_adicionar_item,
        "pode_excluir_item": pode_excluir_item,
        "pode_autorizar_item": pode_autorizar_item,
        "pode_executar": pode_executar,
        "pode_pagar": pode_pagar,
        "pode_remanejar": pode_remanejar,
        "mensagem_edicao": "" if (pode_adicionar_item or pode_autorizar_item or pode_excluir_item) else _msg_edicao(),
        "mensagem_execucao": "" if pode_executar else _msg_execucao(),
        "mensagem_pagamento": "" if pode_pagar else _msg_pagamento(),
        "mensagem_remanejamento": "" if pode_remanejar else _msg_remanejamento(),
    }


def validar_alteracao_estrutural_proposta(proposta_id: int) -> tuple[bool, str]:
    ctx = obter_contexto_fase_proposta(proposta_id)
    if ctx["pode_adicionar_item"] or ctx["pode_excluir_item"]:
        return True, ""
    return False, ctx["mensagem_edicao"] or "Alteração estrutural não permitida para a fase atual."


def validar_autorizacao_proposta(proposta_id: int) -> tuple[bool, str]:
    ctx = obter_contexto_fase_proposta(proposta_id)
    if ctx["pode_autorizar_item"]:
        return True, ""
    return False, ctx["mensagem_edicao"] or "Autorização não permitida para a fase atual."


def validar_execucao_fase(proposta_id: int) -> tuple[bool, str]:
    ctx = obter_contexto_fase_proposta(proposta_id)
    if ctx["pode_executar"]:
        return True, ""
    return False, ctx["mensagem_execucao"] or "Execução não permitida para a fase atual."


def validar_pagamento_fase(proposta_id: int) -> tuple[bool, str]:
    ctx = obter_contexto_fase_proposta(proposta_id)
    if ctx["pode_pagar"]:
        return True, ""
    return False, ctx["mensagem_pagamento"] or "Pagamento não permitido para a fase atual."


def validar_remanejamento_fase(proposta_id: int) -> tuple[bool, str]:
    ctx = obter_contexto_fase_proposta(proposta_id)
    if ctx["pode_remanejar"]:
        return True, ""
    return False, ctx["mensagem_remanejamento"] or "Remanejamento não permitido para a fase atual."
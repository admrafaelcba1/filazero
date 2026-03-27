from services.fase_service import (
    obter_status_proposta,
    validar_execucao_fase,
    validar_pagamento_fase,
    validar_remanejamento_fase,
)


def validar_execucao_por_status(proposta_id: int) -> tuple[bool, str]:
    return validar_execucao_fase(proposta_id)


def validar_pagamento_por_status(proposta_id: int) -> tuple[bool, str]:
    return validar_pagamento_fase(proposta_id)


def validar_remanejamento_por_status(proposta_id: int) -> tuple[bool, str]:
    return validar_remanejamento_fase(proposta_id)
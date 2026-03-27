from __future__ import annotations

from pathlib import Path

from database import get_connection
from services.catalogo_service import importar_catalogo_arquivo_local


def _ja_importado(arquivo_nome: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id
            FROM importacoes
            WHERE tipo = 'CATALOGO_DECRETO_1083'
              AND arquivo_nome = ?
            LIMIT 1
            """,
            (arquivo_nome,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def importar_catalogo_automaticamente_se_existir() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    candidatos = [
        data_dir / "Planilha propostas.xlsx",
        data_dir / "decreto_1083.xlsx",
        data_dir / "decreto_fila_zero_1083.xlsx",
    ]

    for arquivo in candidatos:
        if arquivo.exists():
            if _ja_importado(arquivo.name):
                return
            try:
                importar_catalogo_arquivo_local(arquivo, registrar_importacao=True)
            except Exception:
                pass
            return
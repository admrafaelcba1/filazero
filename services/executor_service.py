from __future__ import annotations

import pandas as pd

from database import get_connection


UF_OPCOES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


def listar_executores(filtro: str = "") -> pd.DataFrame:
    conn = get_connection()
    try:
        if filtro.strip():
            termo = f"%{filtro.strip()}%"
            return pd.read_sql_query(
                """
                SELECT
                    id,
                    cnes,
                    estabelecimento,
                    ibge,
                    municipio,
                    estado,
                    status
                FROM executores
                WHERE cnes LIKE ?
                   OR estabelecimento LIKE ?
                   OR ibge LIKE ?
                   OR municipio LIKE ?
                   OR estado LIKE ?
                ORDER BY estabelecimento
                """,
                conn,
                params=(termo, termo, termo, termo, termo),
            )

        return pd.read_sql_query(
            """
            SELECT
                id,
                cnes,
                estabelecimento,
                ibge,
                municipio,
                estado,
                status
            FROM executores
            ORDER BY estabelecimento
            """,
            conn,
        )
    finally:
        conn.close()


def contar_executores() -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM executores").fetchone()
        return int(row["total"] or 0)
    finally:
        conn.close()


def inserir_ou_atualizar_executor(dados: dict) -> tuple[bool, str]:
    cnes = str(dados.get("cnes", "")).strip()
    estabelecimento = str(dados.get("estabelecimento", "")).strip()

    if not cnes:
        return False, "Informe o CNES."
    if not estabelecimento:
        return False, "Informe o ESTABELECIMENTO."

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO executores (
                cnes,
                estabelecimento,
                ibge,
                municipio,
                estado,
                status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cnes) DO UPDATE SET
                estabelecimento = excluded.estabelecimento,
                ibge = excluded.ibge,
                municipio = excluded.municipio,
                estado = excluded.estado,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cnes,
                estabelecimento,
                str(dados.get("ibge", "")).strip(),
                str(dados.get("municipio", "")).strip(),
                str(dados.get("estado", "")).strip(),
                str(dados.get("status", "Ativo")).strip() or "Ativo",
            ),
        )
        conn.commit()
        return True, "Executor salvo com sucesso."
    finally:
        conn.close()
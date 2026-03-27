from __future__ import annotations

import pandas as pd

from database import get_connection


def listar_proponentes(filtro: str = "") -> pd.DataFrame:
    conn = get_connection()
    try:
        if filtro.strip():
            termo = f"%{filtro.strip()}%"
            return pd.read_sql_query(
                """
                SELECT
                    id,
                    proponente,
                    ibge,
                    cnes,
                    cnpj_fms,
                    nome_completo,
                    status
                FROM proponentes
                WHERE proponente LIKE ?
                   OR ibge LIKE ?
                   OR cnes LIKE ?
                   OR cnpj_fms LIKE ?
                   OR nome_completo LIKE ?
                ORDER BY proponente
                """,
                conn,
                params=(termo, termo, termo, termo, termo),
            )

        return pd.read_sql_query(
            """
            SELECT
                id,
                proponente,
                ibge,
                cnes,
                cnpj_fms,
                nome_completo,
                status
            FROM proponentes
            ORDER BY proponente
            """,
            conn,
        )
    finally:
        conn.close()


def contar_proponentes() -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM proponentes").fetchone()
        return int(row["total"] or 0)
    finally:
        conn.close()


def inserir_ou_atualizar_proponente(dados: dict) -> tuple[bool, str]:
    proponente = str(dados.get("proponente", "")).strip()
    if not proponente:
        return False, "Informe o PROPONENTE."

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO proponentes (
                proponente,
                ibge,
                cnes,
                cnpj_fms,
                nome_completo,
                status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(proponente) DO UPDATE SET
                ibge = excluded.ibge,
                cnes = excluded.cnes,
                cnpj_fms = excluded.cnpj_fms,
                nome_completo = excluded.nome_completo,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                proponente,
                str(dados.get("ibge", "")).strip(),
                str(dados.get("cnes", "")).strip(),
                str(dados.get("cnpj_fms", "")).strip(),
                str(dados.get("nome_completo", "")).strip(),
                str(dados.get("status", "Ativo")).strip() or "Ativo",
            ),
        )
        conn.commit()
        return True, "Proponente salvo com sucesso."
    finally:
        conn.close()
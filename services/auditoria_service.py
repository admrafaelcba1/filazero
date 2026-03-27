from __future__ import annotations

import pandas as pd

from database import get_connection


def registrar_auditoria(
    acao: str,
    entidade: str,
    entidade_id: int | None = None,
    proposta_id: int | None = None,
    item_id: int | None = None,
    detalhes: str = "",
    usuario: str = "SISTEMA",
) -> bool:
    try:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO auditoria_logs (
                    acao,
                    entidade,
                    entidade_id,
                    proposta_id,
                    item_id,
                    usuario,
                    detalhes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (acao or "").strip().upper(),
                    (entidade or "").strip().upper(),
                    entidade_id,
                    proposta_id,
                    item_id,
                    (usuario or "SISTEMA").strip(),
                    (detalhes or "").strip(),
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def listar_auditoria_proposta(proposta_id: int) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id,
                acao,
                entidade,
                entidade_id,
                proposta_id,
                item_id,
                usuario,
                detalhes,
                created_at
            FROM auditoria_logs
            WHERE proposta_id = ?
            ORDER BY id DESC
            """,
            conn,
            params=(proposta_id,),
        )
    finally:
        conn.close()
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from database import get_connection

SHEET_NAME_DECRETO = "BD FILA ZERO 1083"


# =========================================================
# HELPERS
# =========================================================
def _texto(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _codigo_texto(valor, min_len: int = 1) -> str:
    if pd.isna(valor):
        return ""

    if isinstance(valor, float):
        if valor.is_integer():
            valor = int(valor)

    if isinstance(valor, int):
        texto = str(valor)
        return texto.zfill(min_len) if len(texto) < min_len else texto

    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]

    if texto.isdigit() and len(texto) < min_len:
        return texto.zfill(min_len)

    return texto


def _numero(valor) -> float:
    if pd.isna(valor):
        return 0.0

    if isinstance(valor, str):
        texto = valor.strip().replace("R$", "").replace(".", "").replace(",", ".")
        if not texto:
            return 0.0
        try:
            return float(texto)
        except ValueError:
            return 0.0

    try:
        return float(valor)
    except Exception:
        return 0.0


def _derivar_natureza(classificacao: str) -> str:
    cls = (classificacao or "").strip().upper()
    if cls in {"AMB", "HOSP", "AMB/HOSP"}:
        return cls
    return "HOSP"


# =========================================================
# CRUD COMPATÍVEL COM CADASTROS ANTIGOS
# =========================================================
def listar_procedimentos(filtro: str = "", somente_ativos: bool = False) -> pd.DataFrame:
    conn = get_connection()
    try:
        where = []
        params = []

        if filtro.strip():
            termo = f"%{filtro.strip()}%"
            where.append(
                """
                (
                    codigo_sigtap LIKE ?
                    OR descricao_procedimento LIKE ?
                    OR classificacao_interna LIKE ?
                    OR subgrupo_descricao LIKE ?
                )
                """
            )
            params.extend([termo, termo, termo, termo])

        if somente_ativos:
            where.append("COALESCE(ativo, 1) = 1")

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        return pd.read_sql_query(
            f"""
            SELECT
                id,
                codigo_sigtap,
                descricao_procedimento,
                valor_unitario,
                complexidade,
                numeracao,
                registro,
                classificacao_interna,
                subgrupo_cod,
                subgrupo_descricao,
                classificacao,
                natureza,
                origem,
                ativo,
                created_at,
                updated_at
            FROM catalogo_procedimentos
            {where_sql}
            ORDER BY descricao_procedimento
            """,
            conn,
            params=params,
        )
    finally:
        conn.close()


def listar_catalogo(filtro: str = "", somente_ativos: bool = True, limit: int = 1000) -> pd.DataFrame:
    conn = get_connection()
    try:
        where = []
        params = []

        if somente_ativos:
            where.append("COALESCE(ativo, 1) = 1")

        if filtro.strip():
            termo = f"%{filtro.strip()}%"
            where.append(
                """
                (
                    codigo_sigtap LIKE ?
                    OR descricao_procedimento LIKE ?
                    OR classificacao_interna LIKE ?
                    OR subgrupo_descricao LIKE ?
                )
                """
            )
            params.extend([termo, termo, termo, termo])

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        return pd.read_sql_query(
            f"""
            SELECT
                id,
                codigo_sigtap,
                descricao_procedimento,
                valor_unitario,
                complexidade,
                numeracao,
                registro,
                classificacao_interna,
                subgrupo_cod,
                subgrupo_descricao,
                classificacao,
                natureza,
                origem,
                ativo,
                created_at,
                updated_at
            FROM catalogo_procedimentos
            {where_sql}
            ORDER BY descricao_procedimento
            LIMIT {int(limit)}
            """,
            conn,
            params=params,
        )
    finally:
        conn.close()


def obter_procedimento_por_id(procedimento_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                id,
                codigo_sigtap,
                descricao_procedimento,
                valor_unitario,
                complexidade,
                numeracao,
                registro,
                classificacao_interna,
                subgrupo_cod,
                subgrupo_descricao,
                classificacao,
                natureza,
                origem,
                ativo,
                created_at,
                updated_at
            FROM catalogo_procedimentos
            WHERE id = ?
            """,
            (procedimento_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def inserir_ou_atualizar_procedimento(
    codigo_sigtap: str,
    descricao_procedimento: str,
    valor_unitario: float,
    complexidade: str = "",
    numeracao: str = "",
    registro: str = "",
    classificacao_interna: str = "",
    subgrupo_cod: str = "",
    subgrupo_descricao: str = "",
    classificacao: str = "",
    procedimento_id: int | None = None,
    ativo: int = 1,
) -> tuple[bool, str]:
    codigo_sigtap = _codigo_texto(codigo_sigtap, min_len=1)
    descricao_procedimento = _texto(descricao_procedimento)
    classificacao = _texto(classificacao).upper()
    natureza = _derivar_natureza(classificacao)

    if not codigo_sigtap:
        return False, "Informe o código SIGTAP."

    if not descricao_procedimento:
        return False, "Informe a descrição do procedimento."

    conn = get_connection()
    try:
        existente = conn.execute(
            """
            SELECT id
            FROM catalogo_procedimentos
            WHERE codigo_sigtap = ?
              AND (? IS NULL OR id <> ?)
            """,
            (codigo_sigtap, procedimento_id, procedimento_id),
        ).fetchone()

        if existente:
            return False, "Já existe um procedimento com esse código SIGTAP."

        if procedimento_id is None:
            conn.execute(
                """
                INSERT INTO catalogo_procedimentos (
                    codigo_sigtap,
                    descricao_procedimento,
                    valor_unitario,
                    complexidade,
                    numeracao,
                    registro,
                    classificacao_interna,
                    subgrupo_cod,
                    subgrupo_descricao,
                    classificacao,
                    natureza,
                    origem,
                    ativo,
                    codigo,
                    descricao,
                    subgrupo_codigo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    codigo_sigtap,
                    descricao_procedimento,
                    _numero(valor_unitario),
                    _texto(complexidade),
                    _texto(numeracao),
                    _texto(registro),
                    _texto(classificacao_interna),
                    _texto(subgrupo_cod),
                    _texto(subgrupo_descricao),
                    classificacao,
                    natureza,
                    "MANUAL",
                    int(ativo),
                    codigo_sigtap,
                    descricao_procedimento,
                    _texto(subgrupo_cod),
                ),
            )
            conn.commit()
            return True, "Procedimento cadastrado com sucesso."
        else:
            conn.execute(
                """
                UPDATE catalogo_procedimentos
                SET
                    codigo_sigtap = ?,
                    descricao_procedimento = ?,
                    valor_unitario = ?,
                    complexidade = ?,
                    numeracao = ?,
                    registro = ?,
                    classificacao_interna = ?,
                    subgrupo_cod = ?,
                    subgrupo_descricao = ?,
                    classificacao = ?,
                    natureza = ?,
                    ativo = ?,
                    codigo = ?,
                    descricao = ?,
                    subgrupo_codigo = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    codigo_sigtap,
                    descricao_procedimento,
                    _numero(valor_unitario),
                    _texto(complexidade),
                    _texto(numeracao),
                    _texto(registro),
                    _texto(classificacao_interna),
                    _texto(subgrupo_cod),
                    _texto(subgrupo_descricao),
                    classificacao,
                    natureza,
                    int(ativo),
                    codigo_sigtap,
                    descricao_procedimento,
                    _texto(subgrupo_cod),
                    procedimento_id,
                ),
            )
            conn.commit()
            return True, "Procedimento atualizado com sucesso."
    finally:
        conn.close()


def excluir_procedimento(procedimento_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id
            FROM catalogo_procedimentos
            WHERE id = ?
            """,
            (procedimento_id,),
        ).fetchone()

        if not row:
            return False, "Procedimento não encontrado."

        uso = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM proposta_itens
            WHERE codigo_procedimento = (
                SELECT codigo_sigtap
                FROM catalogo_procedimentos
                WHERE id = ?
            )
            """,
            (procedimento_id,),
        ).fetchone()

        if int(uso["total"] or 0) > 0:
            conn.execute(
                """
                UPDATE catalogo_procedimentos
                SET ativo = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (procedimento_id,),
            )
            conn.commit()
            return True, "Procedimento desativado com sucesso, pois já possui uso operacional."

        conn.execute(
            "DELETE FROM catalogo_procedimentos WHERE id = ?",
            (procedimento_id,),
        )
        conn.commit()
        return True, "Procedimento excluído com sucesso."
    finally:
        conn.close()


# =========================================================
# IMPORTAÇÃO DO DECRETO
# =========================================================
def carregar_aba_decreto_excel(excel_source) -> pd.DataFrame:
    return pd.read_excel(
        excel_source,
        sheet_name=SHEET_NAME_DECRETO,
        header=1,
    )


def preparar_dataframe_catalogo(df_raw: pd.DataFrame) -> pd.DataFrame:
    mapa = {
        "CÓDIGO\nSIGTAP": "codigo_sigtap",
        "DESCRIÇÃO DO PROCEDIMENTO": "descricao_procedimento",
        "VALOR UNITÁRIO": "valor_unitario",
        "COMPLEXIDADE": "complexidade",
        "NUMERAÇÃO": "numeracao",
        "REGISTRO": "registro",
        "CLASSIFICAÇÃO INTERNA": "classificacao_interna",
        "SUB-GRUPO-COD": "subgrupo_cod",
        "SUB-GRUPO-DESCRIÇÃO": "subgrupo_descricao",
        "CLASSIFICAÇÃO": "classificacao",
    }

    df = df_raw.rename(columns=mapa).copy()

    colunas_necessarias = list(mapa.values())
    for coluna in colunas_necessarias:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas_necessarias].copy()

    df["codigo_sigtap"] = df["codigo_sigtap"].apply(lambda x: _codigo_texto(x, min_len=1))
    df["descricao_procedimento"] = df["descricao_procedimento"].apply(_texto)
    df["valor_unitario"] = df["valor_unitario"].apply(_numero)
    df["complexidade"] = df["complexidade"].apply(_texto)
    df["numeracao"] = df["numeracao"].apply(_texto)
    df["registro"] = df["registro"].apply(_texto)
    df["classificacao_interna"] = df["classificacao_interna"].apply(_texto)
    df["subgrupo_cod"] = df["subgrupo_cod"].apply(lambda x: _codigo_texto(x, min_len=1))
    df["subgrupo_descricao"] = df["subgrupo_descricao"].apply(_texto)
    df["classificacao"] = df["classificacao"].apply(_texto).str.upper()

    df["natureza"] = df["classificacao"].apply(_derivar_natureza)
    df["origem"] = "DECRETO_1083"
    df["ativo"] = 1

    df = df[df["codigo_sigtap"] != ""].copy()
    df = df[df["descricao_procedimento"] != ""].copy()
    df = df.drop_duplicates(subset=["codigo_sigtap"], keep="first").reset_index(drop=True)

    return df


def importar_catalogo_dataframe(
    df_catalogo: pd.DataFrame,
    arquivo_nome: str = "",
    registrar_importacao: bool = True,
) -> dict:
    conn = get_connection()
    inseridos = 0
    atualizados = 0
    ignorados = 0
    erros = []

    try:
        for idx, row in df_catalogo.iterrows():
            try:
                codigo = _texto(row["codigo_sigtap"])
                descricao = _texto(row["descricao_procedimento"])

                if not codigo or not descricao:
                    ignorados += 1
                    continue

                existente = conn.execute(
                    """
                    SELECT id
                    FROM catalogo_procedimentos
                    WHERE codigo_sigtap = ?
                    """,
                    (codigo,),
                ).fetchone()

                if existente:
                    conn.execute(
                        """
                        UPDATE catalogo_procedimentos
                        SET
                            descricao_procedimento = ?,
                            valor_unitario = ?,
                            complexidade = ?,
                            numeracao = ?,
                            registro = ?,
                            classificacao_interna = ?,
                            subgrupo_cod = ?,
                            subgrupo_descricao = ?,
                            classificacao = ?,
                            natureza = ?,
                            origem = ?,
                            ativo = ?,
                            codigo = ?,
                            descricao = ?,
                            subgrupo_codigo = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE codigo_sigtap = ?
                        """,
                        (
                            descricao,
                            _numero(row["valor_unitario"]),
                            _texto(row["complexidade"]),
                            _texto(row["numeracao"]),
                            _texto(row["registro"]),
                            _texto(row["classificacao_interna"]),
                            _texto(row["subgrupo_cod"]),
                            _texto(row["subgrupo_descricao"]),
                            _texto(row["classificacao"]).upper(),
                            _texto(row["natureza"]),
                            _texto(row["origem"]),
                            int(row["ativo"]) if not pd.isna(row["ativo"]) else 1,
                            codigo,
                            descricao,
                            _texto(row["subgrupo_cod"]),
                            codigo,
                        ),
                    )
                    atualizados += 1
                else:
                    conn.execute(
                        """
                        INSERT INTO catalogo_procedimentos (
                            codigo_sigtap,
                            descricao_procedimento,
                            valor_unitario,
                            complexidade,
                            numeracao,
                            registro,
                            classificacao_interna,
                            subgrupo_cod,
                            subgrupo_descricao,
                            classificacao,
                            natureza,
                            origem,
                            ativo,
                            codigo,
                            descricao,
                            subgrupo_codigo
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            codigo,
                            descricao,
                            _numero(row["valor_unitario"]),
                            _texto(row["complexidade"]),
                            _texto(row["numeracao"]),
                            _texto(row["registro"]),
                            _texto(row["classificacao_interna"]),
                            _texto(row["subgrupo_cod"]),
                            _texto(row["subgrupo_descricao"]),
                            _texto(row["classificacao"]).upper(),
                            _texto(row["natureza"]),
                            _texto(row["origem"]),
                            int(row["ativo"]) if not pd.isna(row["ativo"]) else 1,
                            codigo,
                            descricao,
                            _texto(row["subgrupo_cod"]),
                        ),
                    )
                    inseridos += 1

            except Exception as e:
                erros.append(f"Linha {idx + 2}: {e}")

        if registrar_importacao:
            conn.execute(
                """
                INSERT INTO importacoes (
                    tipo,
                    arquivo_nome,
                    total_registros
                )
                VALUES (?, ?, ?)
                """,
                ("CATALOGO_DECRETO_1083", arquivo_nome, int(len(df_catalogo))),
            )

        conn.commit()

        return {
            "ok": True,
            "mensagem": "Importação concluída com sucesso.",
            "inseridos": inseridos,
            "atualizados": atualizados,
            "ignorados": ignorados,
            "erros": erros,
            "total_processado": int(len(df_catalogo)),
        }
    finally:
        conn.close()


def importar_catalogo_upload(uploaded_file) -> dict:
    conteudo = uploaded_file.getvalue()
    excel_source = BytesIO(conteudo)
    df_raw = carregar_aba_decreto_excel(excel_source)
    df_catalogo = preparar_dataframe_catalogo(df_raw)
    return importar_catalogo_dataframe(
        df_catalogo=df_catalogo,
        arquivo_nome=getattr(uploaded_file, "name", "upload_excel"),
        registrar_importacao=True,
    )


def importar_catalogo_arquivo_local(file_path: str | Path, registrar_importacao: bool = True) -> dict:
    file_path = Path(file_path)
    df_raw = carregar_aba_decreto_excel(file_path)
    df_catalogo = preparar_dataframe_catalogo(df_raw)
    return importar_catalogo_dataframe(
        df_catalogo=df_catalogo,
        arquivo_nome=file_path.name,
        registrar_importacao=registrar_importacao,
    )


def obter_resumo_catalogo() -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_procedimentos,
                COALESCE(SUM(CASE WHEN COALESCE(ativo, 1) = 1 THEN 1 ELSE 0 END), 0) AS total_ativos,
                COALESCE(SUM(CASE WHEN classificacao = 'AMB' THEN 1 ELSE 0 END), 0) AS total_amb,
                COALESCE(SUM(CASE WHEN classificacao = 'HOSP' THEN 1 ELSE 0 END), 0) AS total_hosp,
                COALESCE(SUM(CASE WHEN classificacao = 'AMB/HOSP' THEN 1 ELSE 0 END), 0) AS total_amb_hosp
            FROM catalogo_procedimentos
            """
        ).fetchone()

        ultima_importacao = conn.execute(
            """
            SELECT arquivo_nome, total_registros, created_at
            FROM importacoes
            WHERE tipo = 'CATALOGO_DECRETO_1083'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        return {
            "total_procedimentos": int(row["total_procedimentos"] or 0),
            "total_ativos": int(row["total_ativos"] or 0),
            "total_amb": int(row["total_amb"] or 0),
            "total_hosp": int(row["total_hosp"] or 0),
            "total_amb_hosp": int(row["total_amb_hosp"] or 0),
            "ultima_importacao": dict(ultima_importacao) if ultima_importacao else None,
        }
    finally:
        conn.close()


def gerar_planilha_modelo_catalogo() -> bytes:
    colunas = [
        "CÓDIGO SIGTAP",
        "DESCRIÇÃO DO PROCEDIMENTO",
        "VALOR UNITÁRIO",
        "COMPLEXIDADE",
        "NUMERAÇÃO",
        "REGISTRO",
        "CLASSIFICAÇÃO INTERNA",
        "SUB-GRUPO-COD",
        "SUB-GRUPO-DESCRIÇÃO",
        "CLASSIFICAÇÃO",
    ]
    df_modelo = pd.DataFrame(columns=colunas)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_modelo.to_excel(writer, sheet_name=SHEET_NAME_DECRETO, index=False)

    output.seek(0)
    return output.getvalue()
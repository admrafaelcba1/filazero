import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "fila_zero.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _get_existing_columns(conn, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_column(conn, table_name: str, column_name: str, column_def: str):
    if not _table_exists(conn, table_name):
        return
    existing = _get_existing_columns(conn, table_name)
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def _ensure_remanejamentos_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS remanejamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposta_id INTEGER NOT NULL,
            item_origem_id INTEGER NOT NULL,
            item_destino_id INTEGER NOT NULL,
            quantidade_origem_remanejada INTEGER NOT NULL,
            valor_origem_remanejado REAL NOT NULL,
            quantidade_destino_acrescida INTEGER NOT NULL,
            valor_destino_acrescido REAL NOT NULL,
            saldo_residual REAL DEFAULT 0,
            justificativa TEXT,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id),
            FOREIGN KEY (item_origem_id) REFERENCES proposta_itens(id),
            FOREIGN KEY (item_destino_id) REFERENCES proposta_itens(id)
        )
        """
    )


def _ensure_auditoria_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao TEXT NOT NULL,
            entidade TEXT NOT NULL,
            entidade_id INTEGER,
            proposta_id INTEGER,
            item_id INTEGER,
            usuario TEXT DEFAULT 'SISTEMA',
            detalhes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id),
            FOREIGN KEY (item_id) REFERENCES proposta_itens(id)
        )
        """
    )


def criar_tabelas():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS beneficiarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT,
            municipio TEXT,
            cnes TEXT,
            status TEXT DEFAULT 'Ativo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS catalogo_procedimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_sigtap TEXT NOT NULL UNIQUE,
            descricao_procedimento TEXT NOT NULL,
            valor_unitario REAL DEFAULT 0,
            complexidade TEXT,
            numeracao TEXT,
            registro TEXT,
            classificacao_interna TEXT,
            subgrupo_cod TEXT,
            subgrupo_descricao TEXT,
            classificacao TEXT,
            origem TEXT DEFAULT 'MANUAL',
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proponentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proponente TEXT NOT NULL UNIQUE,
            ibge TEXT,
            cnes TEXT,
            cnpj_fms TEXT,
            nome_completo TEXT,
            status TEXT DEFAULT 'Ativo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS executores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnes TEXT NOT NULL UNIQUE,
            estabelecimento TEXT NOT NULL,
            ibge TEXT,
            municipio TEXT,
            estado TEXT,
            status TEXT DEFAULT 'Ativo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_proposta TEXT NOT NULL UNIQUE,
            proponente_id INTEGER,
            proponente TEXT,
            ordem_proposta INTEGER DEFAULT 1,
            competencia_mes INTEGER,
            competencia_ano INTEGER,
            quantidade_proposta INTEGER DEFAULT 0,
            quantidade_proc_diversos INTEGER DEFAULT 0,
            quantidade_cirurgia INTEGER DEFAULT 0,
            valor_total REAL DEFAULT 0,
            valor_aprovado REAL DEFAULT 0,
            status TEXT DEFAULT 'EM ELABORACAO',
            origem_recurso TEXT,
            deputado TEXT,
            parecer_tecnico TEXT,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proponente_id) REFERENCES proponentes(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proposta_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposta_id INTEGER NOT NULL,
            codigo_procedimento TEXT NOT NULL,
            descricao_procedimento TEXT NOT NULL,
            quantidade INTEGER DEFAULT 0,
            quantidade_autorizada INTEGER DEFAULT 0,
            valor_unitario REAL DEFAULT 0,
            valor_total REAL DEFAULT 0,
            valor_autorizado REAL DEFAULT 0,
            classificacao TEXT,
            subgrupo TEXT,
            natureza TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS execucao_hospitalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposta_id INTEGER NOT NULL,
            item_proposta_id INTEGER NOT NULL,
            executor_id INTEGER,
            cnes_executor TEXT,
            competencia_mes INTEGER,
            competencia_ano INTEGER,
            quantidade INTEGER DEFAULT 0,
            valor_total REAL DEFAULT 0,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id),
            FOREIGN KEY (item_proposta_id) REFERENCES proposta_itens(id),
            FOREIGN KEY (executor_id) REFERENCES executores(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS execucao_ambulatorial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposta_id INTEGER NOT NULL,
            item_proposta_id INTEGER NOT NULL,
            executor_id INTEGER,
            cnes_executor TEXT,
            competencia_mes INTEGER,
            competencia_ano INTEGER,
            quantidade INTEGER DEFAULT 0,
            valor_total REAL DEFAULT 0,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id),
            FOREIGN KEY (item_proposta_id) REFERENCES proposta_itens(id),
            FOREIGN KEY (executor_id) REFERENCES executores(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposta_id INTEGER NOT NULL,
            item_proposta_id INTEGER,
            executor_id INTEGER,
            cnes_executor TEXT,
            tipo_execucao TEXT,
            valor_pago REAL DEFAULT 0,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposta_id) REFERENCES propostas(id),
            FOREIGN KEY (item_proposta_id) REFERENCES proposta_itens(id),
            FOREIGN KEY (executor_id) REFERENCES executores(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS importacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            arquivo_nome TEXT,
            total_registros INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_remanejamentos_table(conn)
    _ensure_auditoria_table(conn)

    _ensure_column(conn, "catalogo_procedimentos", "codigo", "TEXT")
    _ensure_column(conn, "catalogo_procedimentos", "descricao", "TEXT")
    _ensure_column(conn, "catalogo_procedimentos", "subgrupo_codigo", "TEXT")
    _ensure_column(conn, "catalogo_procedimentos", "natureza", "TEXT")

    _ensure_column(conn, "propostas", "proponente_id", "INTEGER")
    _ensure_column(conn, "propostas", "proponente", "TEXT")
    _ensure_column(conn, "propostas", "ordem_proposta", "INTEGER DEFAULT 1")
    _ensure_column(conn, "propostas", "competencia_mes", "INTEGER")
    _ensure_column(conn, "propostas", "competencia_ano", "INTEGER")
    _ensure_column(conn, "propostas", "quantidade_proposta", "INTEGER DEFAULT 0")
    _ensure_column(conn, "propostas", "quantidade_proc_diversos", "INTEGER DEFAULT 0")
    _ensure_column(conn, "propostas", "quantidade_cirurgia", "INTEGER DEFAULT 0")
    _ensure_column(conn, "propostas", "valor_total", "REAL DEFAULT 0")
    _ensure_column(conn, "propostas", "valor_aprovado", "REAL DEFAULT 0")
    _ensure_column(conn, "propostas", "status", "TEXT DEFAULT 'EM ELABORACAO'")
    _ensure_column(conn, "propostas", "origem_recurso", "TEXT")
    _ensure_column(conn, "propostas", "deputado", "TEXT")
    _ensure_column(conn, "propostas", "parecer_tecnico", "TEXT")
    _ensure_column(conn, "propostas", "observacao", "TEXT")
    _ensure_column(conn, "propostas", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    _ensure_column(conn, "proposta_itens", "quantidade", "INTEGER DEFAULT 0")
    _ensure_column(conn, "proposta_itens", "quantidade_autorizada", "INTEGER DEFAULT 0")
    _ensure_column(conn, "proposta_itens", "valor_unitario", "REAL DEFAULT 0")
    _ensure_column(conn, "proposta_itens", "valor_total", "REAL DEFAULT 0")
    _ensure_column(conn, "proposta_itens", "valor_autorizado", "REAL DEFAULT 0")
    _ensure_column(conn, "proposta_itens", "classificacao", "TEXT")
    _ensure_column(conn, "proposta_itens", "subgrupo", "TEXT")
    _ensure_column(conn, "proposta_itens", "natureza", "TEXT")
    _ensure_column(conn, "proposta_itens", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    _ensure_column(conn, "execucao_hospitalar", "executor_id", "INTEGER")
    _ensure_column(conn, "execucao_hospitalar", "cnes_executor", "TEXT")
    _ensure_column(conn, "execucao_hospitalar", "competencia_mes", "INTEGER")
    _ensure_column(conn, "execucao_hospitalar", "competencia_ano", "INTEGER")
    _ensure_column(conn, "execucao_hospitalar", "quantidade", "INTEGER DEFAULT 0")
    _ensure_column(conn, "execucao_hospitalar", "valor_total", "REAL DEFAULT 0")
    _ensure_column(conn, "execucao_hospitalar", "observacao", "TEXT")
    _ensure_column(conn, "execucao_hospitalar", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    _ensure_column(conn, "execucao_ambulatorial", "executor_id", "INTEGER")
    _ensure_column(conn, "execucao_ambulatorial", "cnes_executor", "TEXT")
    _ensure_column(conn, "execucao_ambulatorial", "competencia_mes", "INTEGER")
    _ensure_column(conn, "execucao_ambulatorial", "competencia_ano", "INTEGER")
    _ensure_column(conn, "execucao_ambulatorial", "quantidade", "INTEGER DEFAULT 0")
    _ensure_column(conn, "execucao_ambulatorial", "valor_total", "REAL DEFAULT 0")
    _ensure_column(conn, "execucao_ambulatorial", "observacao", "TEXT")
    _ensure_column(conn, "execucao_ambulatorial", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    _ensure_column(conn, "pagamentos", "executor_id", "INTEGER")
    _ensure_column(conn, "pagamentos", "cnes_executor", "TEXT")
    _ensure_column(conn, "pagamentos", "tipo_execucao", "TEXT")
    _ensure_column(conn, "pagamentos", "valor_pago", "REAL DEFAULT 0")
    _ensure_column(conn, "pagamentos", "observacao", "TEXT")
    _ensure_column(conn, "pagamentos", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    conn.commit()
    conn.close()
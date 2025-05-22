import sqlite3
from typing import List, Tuple, Any, Optional

DB_NAME = "advocacia_data.db"

class DBHandler:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """Conecta ao banco de dados SQLite."""
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row # Permite acesso às colunas por nome
        self.cursor = self.conn.cursor()

    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> None:
        """Executa uma query que não retorna dados (INSERT, UPDATE, DELETE)."""
        self.connect()
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao executar query: {e}")
            if self.conn:
                self.conn.rollback() # Desfaz a transação em caso de erro
        finally:
            self.close()

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """Executa uma query e retorna uma única linha."""
        self.connect()
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Erro ao buscar um registro: {e}")
            return None
        finally:
            self.close()

    def fetch_all(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Executa uma query e retorna todas as linhas."""
        self.connect()
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar todos os registros: {e}")
            return []
        finally:
            self.close()

    def get_last_row_id(self) -> Optional[int]:
        """Retorna o ID da última linha inserida."""
        if self.cursor:
            return self.cursor.lastrowid
        return None

    def setup_tables(self):
        """Cria as tabelas no banco de dados, se não existirem."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                telefone TEXT,
                email TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS processos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT UNIQUE NOT NULL,
                cliente_id INTEGER,
                descricao TEXT,
                status TEXT, -- Ex: Em andamento, Concluído, Arquivado
                data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS demandas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id INTEGER,
                descricao TEXT NOT NULL,
                prazo_final DATE,
                status TEXT, -- Ex: Pendente, Em andamento, Concluída
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processo_id) REFERENCES processos (id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS audiencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id INTEGER,
                data_hora DATETIME NOT NULL,
                local TEXT,
                vara TEXT,
                tipo TEXT, -- Ex: Instrução, Conciliação
                notas TEXT,
                FOREIGN KEY (processo_id) REFERENCES processos (id) ON DELETE CASCADE
            );
            """
            # Adicionar outras tabelas conforme necessário (ex: usuários, se não usar AWS para tudo)
        ]
        self.connect()
        try:
            for query in queries:
                self.cursor.execute(query)
            self.conn.commit()
            print("Tabelas configuradas/verificadas com sucesso.")
        except sqlite3.Error as e:
            print(f"Erro ao configurar tabelas: {e}")
        finally:
            self.close()

# Exemplo de uso (geralmente chamado uma vez no início do app)
if __name__ == "__main__":
    db_handler = DBHandler()
    db_handler.setup_tables()
    print(f"Banco de dados '{DB_NAME}' e tabelas prontas para uso.")

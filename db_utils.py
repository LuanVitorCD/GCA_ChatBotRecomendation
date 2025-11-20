# db_utils.py - Funções para interagir com o banco de dados PostgreSQL
# VERSÃO CORRIGIDA: Tratamento de ID string vs inteiro
import psycopg2
import pandas as pd
from typing import Optional

# --- ATENÇÃO ---
# Modifique com as suas credenciais do PostgreSQL.
DB_SETTINGS = {
    "host": "localhost",
    "database": "postgres",
    "user": "postgres",
    "password": "admin" # Troque pela sua senha
}

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise

def get_professors_data():
    """Busca os dados agregados dos professores no banco de dados."""
    query = """
    SELECT p.id, p.nome AS name,
           COALESCE(STRING_AGG(pu.titulo, ' '), 'Nenhuma publicação encontrada') AS research
    FROM pessoa p
    LEFT JOIN publicacao pu ON p.id = pu.id_pessoa
    GROUP BY p.id, p.nome ORDER BY p.nome;
    """
    conn = None
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Ocorreu um erro ao buscar os dados dos professores: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_publications_by_professor_id(professor_identifier: str, limit: Optional[int] = 10):
    """
    Busca as publicações de um professor.
    
    CORREÇÃO DE ERRO:
    Esta função agora aceita tanto um ID numérico (int) quanto um Nome (str).
    Se receber um nome (ex: 'cláudia_tirelli'), ela primeiro busca o ID numérico
    na tabela 'pessoa' antes de consultar a tabela 'publicacao'.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            prof_id_int = None
            
            # --- LÓGICA DE RESOLUÇÃO DE ID ---
            # 1. Verifica se o identificador já é um número (string numérica ou int)
            if str(professor_identifier).isdigit():
                prof_id_int = int(professor_identifier)
            else:
                # 2. Se for texto (ex: slug do motor legado), tenta encontrar o ID pelo nome
                # Remove underscores e tenta limpar o nome para a busca
                clean_name = str(professor_identifier).replace("_", " ").replace("legacy ", "").strip()
                
                print(f"Tentando resolver ID para o nome: '{clean_name}'")
                
                # Tenta busca exata ou parcial (ILIKE é case-insensitive no Postgres)
                # Usamos '%' para permitir match parcial se o nome não for exato
                cur.execute("SELECT id FROM pessoa WHERE nome ILIKE %s LIMIT 1;", (f"%{clean_name}%",))
                result = cur.fetchone()
                
                if result:
                    prof_id_int = result[0]
                    print(f"ID encontrado: {prof_id_int}")
                else:
                    print(f"Aviso: Professor '{clean_name}' não encontrado na tabela 'pessoa'.")
                    return [], 0

            # Se falhou em achar um ID numérico, retorna vazio sem quebrar o app
            if prof_id_int is None:
                return [], 0

            # --- BUSCA DE PUBLICAÇÕES (Agora usando ID Inteiro Garantido) ---
            count_query = "SELECT COUNT(*) FROM publicacao WHERE id_pessoa = %s;"
            cur.execute(count_query, (prof_id_int,))
            total_count = cur.fetchone()[0]

            if limit is not None:
                pubs_query = "SELECT titulo FROM publicacao WHERE id_pessoa = %s ORDER BY ano DESC LIMIT %s;"
                cur.execute(pubs_query, (prof_id_int, limit))
            else:
                pubs_query = "SELECT titulo FROM publicacao WHERE id_pessoa = %s ORDER BY ano DESC;"
                cur.execute(pubs_query, (prof_id_int,))
            
            publications = [item[0] for item in cur.fetchall()]
        
        return publications, total_count

    except Exception as e:
        print(f"Erro ao buscar publicações para '{professor_identifier}': {e}")
        # Retorna lista vazia em vez de quebrar a execução
        return [], 0
    finally:
        if conn:
            conn.close()

# Teste rápido
"""
if __name__ == '__main__':
    try:
        print("Teste de resolução de nome para ID...")
        pubs, total = get_publications_by_professor_id("cláudia_tirelli", limit=3)
        print(f"Resultado para 'cláudia_tirelli': {len(pubs)} publicações encontradas.")
    except Exception as e:
        print(f"Erro no teste: {e}")
"""
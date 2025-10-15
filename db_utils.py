# db_utils.py - Funções para interagir com o banco de dados PostgreSQL
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

def get_publications_by_professor_id(professor_id: str, limit: Optional[int] = 10):
    """
    Busca as publicações de um professor e o total de publicações.
    Se o limite for None, busca todas.
    Retorna: (lista_de_publicacoes, contagem_total)
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Primeiro, obtém a contagem total
            count_query = "SELECT COUNT(*) FROM publicacao WHERE id_pessoa = %s;"
            cur.execute(count_query, (professor_id,))
            total_count = cur.fetchone()[0]

            # Depois, busca as publicações com ou sem limite
            if limit is not None:
                pubs_query = "SELECT titulo FROM publicacao WHERE id_pessoa = %s ORDER BY ano DESC LIMIT %s;"
                cur.execute(pubs_query, (professor_id, limit))
            else:
                pubs_query = "SELECT titulo FROM publicacao WHERE id_pessoa = %s ORDER BY ano DESC;"
                cur.execute(pubs_query, (professor_id,))
            
            publications = [item[0] for item in cur.fetchall()]
        return publications, total_count
    except Exception as e:
        print(f"Erro ao buscar publicações para o professor ID {professor_id}: {e}")
        return [], 0
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Testando a busca de dados do banco...")
    try:
        professors = get_professors_data()
        if professors:
            print(f"Sucesso! Encontrados {len(professors)} professores.")
            prof_id = professors[0].get('id')
            if prof_id:
                print(f"\nTestando busca de 5 publicações para o professor ID: {prof_id}")
                pubs, total = get_publications_by_professor_id(prof_id, limit=5)
                if pubs:
                    print(f"Encontradas {len(pubs)} de {total} publicações. Exemplo:")
                    for pub in pubs:
                        print(f"- {pub}")
                else:
                    print("Nenhuma publicação encontrada para este professor.")
        else:
            print("A consulta funcionou, mas nenhum professor foi retornado.")
    except Exception as e:
        print(f"Falha no teste de conexão: {e}")


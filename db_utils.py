# db_utils.py - Funções para interagir com o banco de dados PostgreSQL
import psycopg2
import pandas as pd

# --- ATENÇÃO ---
# Modifique com as suas credenciais do PostgreSQL.
# Em um ambiente de produção, use variáveis de ambiente!
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
    """
    Busca os dados dos professores no banco de dados e formata
    para a função de recomendação.

    Esta função agrega os títulos das publicações de cada professor
    para criar um campo 'research' que representa sua área de pesquisa.
    """
    query = """
    SELECT 
        p.id, 
        p.nome AS name,
        -- Concatena os títulos das publicações para formar a linha de pesquisa
        -- Usamos COALESCE para tratar casos onde não há publicações
        COALESCE(STRING_AGG(pu.titulo, ' '), 'Nenhuma publicação encontrada') AS research
    FROM 
        pessoa p
    LEFT JOIN 
        publicacao pu ON p.id = pu.id_pessoa
    GROUP BY 
        p.id, p.nome
    ORDER BY
        p.nome;
    """
    
    conn = None
    try:
        conn = get_db_connection()
        # Usamos pandas para ler o resultado da query diretamente em um DataFrame
        df = pd.read_sql_query(query, conn)
        
        # A função de recomendação espera uma lista de dicionários
        return df.to_dict(orient='records')

    except Exception as e:
        print(f"Ocorreu um erro ao buscar os dados dos professores: {e}")
        raise # Propaga a exceção para ser tratada no app principal
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Bloco para testar a função diretamente
    print("Testando a busca de dados do banco...")
    try:
        professors = get_professors_data()
        if professors:
            print(f"Sucesso! Encontrados {len(professors)} professores.")
            print("Exemplo do primeiro professor:")
            print(professors[0])
        else:
            print("A consulta funcionou, mas nenhum professor foi retornado da base de dados.")
    except Exception as e:
        print(f"Falha no teste de conexão: {e}")

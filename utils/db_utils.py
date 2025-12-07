# db_utils.py - Adaptado para encontrar o banco na pasta data/ ou raiz
import sqlite3
import os

# Define o caminho relativo para a pasta data/ dentro do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Tenta primeiro na pasta data/, depois na raiz
DB_PATH_DATA = os.path.join(BASE_DIR, '../data', 'base_recomendacao.db')
DB_PATH_ROOT = os.path.join(BASE_DIR, '../base_recomendacao.db')

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco SQLite.
    Verifica se o arquivo existe na pasta 'data/' ou na raiz.
    """
    final_path = None
    
    if os.path.exists(DB_PATH_DATA):
        final_path = DB_PATH_DATA
    elif os.path.exists(DB_PATH_ROOT):
        final_path = DB_PATH_ROOT
    else:
        raise FileNotFoundError(
            f"Banco de dados não encontrado.\n"
            f"Esperado em: {DB_PATH_DATA} ou {DB_PATH_ROOT}\n"
            "Certifique-se de extrair o arquivo 'base_recomendacao.db'."
        )
    
    conn = sqlite3.connect(final_path)
    # Permite acessar colunas pelo nome (row['nome'])
    conn.row_factory = sqlite3.Row 
    return conn

def get_publications_by_professor_id(professor_identifier, limit=10):
    """
    Busca publicações compatível com SQLite.
    Aceita ID (int) ou Nome (str).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        prof_id_int = None
        
        # 1. Resolução de ID (Nome -> Int)
        if str(professor_identifier).isdigit():
            prof_id_int = int(professor_identifier)
        else:
            # Limpeza do nome (slug -> nome real aproximado)
            clean_name = str(professor_identifier).replace("_", " ").replace("legacy ", "").strip()
            cur.execute("SELECT id FROM pessoa WHERE nome LIKE ? LIMIT 1", (f"%{clean_name}%",))
            result = cur.fetchone()
            if result:
                prof_id_int = result['id']
            else:
                return [], 0

        if prof_id_int is None: return [], 0

        # 2. Busca de Publicações
        cur.execute("SELECT COUNT(*) as count FROM publicacao WHERE id_pessoa = ?", (prof_id_int,))
        total_count = cur.fetchone()['count']

        sql = "SELECT titulo FROM publicacao WHERE id_pessoa = ? ORDER BY ano DESC"
        if limit: sql += f" LIMIT {limit}"
            
        cur.execute(sql, (prof_id_int,))
        publications = [item['titulo'] for item in cur.fetchall()]
        
        return publications, total_count

    except Exception as e:
        print(f"Erro no DB Utils: {e}")
        return [], 0
    finally:
        if conn: conn.close()
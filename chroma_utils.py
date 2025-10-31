# chroma_utils.py - Funções para interagir com o ChromaDB (versão corrigida e final)
import chromadb
import pandas as pd
import streamlit as st
from db_utils import get_db_connection

def sync_postgres_to_chroma(collection):
    """
    Busca dados do PostgreSQL e os insere na coleção FORNECIDA do ChromaDB.
    A lógica agora limpa os itens da coleção em vez de recriá-la.
    """
    if collection is None:
        raise ValueError("A coleção do ChromaDB não foi inicializada corretamente.")
        
    print("Iniciando sincronização: PostgreSQL -> ChromaDB")
    
    try:
        conn = get_db_connection()
        sql_query = """
        WITH publicacoes_agg AS (
            SELECT 
                id_pessoa, 
                COUNT(*) as publicacoes_count,
                STRING_AGG(titulo, '. ') as research_text
            FROM publicacao
            GROUP BY id_pessoa
        ),
        orientacoes_agg AS (
            SELECT id_pessoa, COUNT(*) as orientacoes_count FROM orientacao GROUP BY id_pessoa
        ),
        qualis_agg AS (
            SELECT p.id_pessoa, 
                   AVG(CASE q.estrato WHEN 'A1' THEN 100 WHEN 'A2' THEN 87.5 WHEN 'B1' THEN 50 ELSE 20 END) as qualis_score
            FROM publicacao p JOIN qualis q ON REPLACE(p.issn, '-', '') = REPLACE(q.issn, '-', '')
            GROUP BY p.id_pessoa
        ),
        areas_agg AS (
            -- CORREÇÃO: Adicionado TRIM() e filtro para remover valores nulos ou vazios
            SELECT id_pessoa, STRING_AGG(DISTINCT TRIM(area_conhecimento), ', ') as areas
            FROM area_conhecimento
            WHERE area_conhecimento IS NOT NULL AND TRIM(area_conhecimento) <> ''
            GROUP BY id_pessoa
        ),
        doutorado_agg AS (
            SELECT pp.id_pessoa, BOOL_OR(p.doutorado) as tem_doutorado
            FROM pessoa_ppg pp JOIN ppg p ON pp.id_ppg = p.id
            GROUP BY pp.id_pessoa
        )
        SELECT 
            p.id as id_pessoa, p.nome as nome_pessoa,
            COALESCE(pa.publicacoes_count, 0) as publicacoes_count,
            COALESCE(oa.orientacoes_count, 0) as orientacoes_count,
            COALESCE(qa.qualis_score, 0) as qualis_score,
            -- CORREÇÃO: Define 'Não informado' como padrão no SQL se o JOIN falhar
            COALESCE(aa.areas, 'Não informado') as areas,
            COALESCE(da.tem_doutorado, FALSE) as tem_doutorado,
            -- CORREÇÃO: Coalesce mais robusto para research_text
            COALESCE(pa.research_text, p.nome, 'Sem descrição de pesquisa detalhada') as research_text
        FROM pessoa p
        LEFT JOIN publicacoes_agg pa ON p.id = pa.id_pessoa
        LEFT JOIN orientacoes_agg oa ON p.id = oa.id_pessoa
        LEFT JOIN qualis_agg qa ON p.id = qa.id_pessoa
        LEFT JOIN areas_agg aa ON p.id = aa.id_pessoa
        LEFT JOIN doutorado_agg da ON p.id = da.id_pessoa;
        """
        professors_df = pd.read_sql_query(sql_query, conn)
        conn.close()
    except Exception as e:
        print(f"ERRO ao buscar dados do PostgreSQL: {e}")
        raise e

    if professors_df.empty:
        print("Nenhum professor encontrado no PostgreSQL para sincronizar.")
        return 0

    # --- CORREÇÃO DEFINITIVA ---
    # 1. Pegamos os IDs de todos os documentos que já existem na coleção.
    existing_ids = collection.get(include=[])['ids']
    if existing_ids:
        # 2. Se existirem IDs, nós os deletamos. Isso limpa a coleção sem destruí-la.
        print(f"Limpando {len(existing_ids)} registros antigos da coleção...")
        collection.delete(ids=existing_ids)

    # 3. Agora, adicionamos os novos dados à coleção agora vazia.
    for col in ['publicacoes_count', 'orientacoes_count']:
        professors_df[col] = professors_df[col].astype(int)
    professors_df['qualis_score'] = professors_df['qualis_score'].astype(float)
    professors_df['id_pessoa'] = professors_df['id_pessoa'].astype(str)
    
    # CORREÇÃO: Garante que nulos/vazios do Python também sejam tratados
    professors_df['research_text'] = professors_df['research_text'].fillna('Sem descrição de pesquisa detalhada')
    professors_df['research_text'] = professors_df['research_text'].replace('', 'Sem descrição de pesquisa detalhada')
    
    professors_df['areas'] = professors_df['areas'].fillna('Não informado')
    professors_df['areas'] = professors_df['areas'].replace('', 'Não informado')

    documents = professors_df['research_text'].tolist()
    metadatas = professors_df.drop(columns=['research_text']).to_dict(orient='records')
    ids = professors_df['id_pessoa'].tolist()

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"Sincronização concluída. {len(ids)} orientadores adicionados ao ChromaDB.")
        return len(ids)
        
    return 0


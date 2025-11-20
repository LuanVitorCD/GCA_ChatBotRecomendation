# recommend_chroma.py - Lógica de recomendação Híbrida (versão corrigida)
import pandas as pd

def recommend_hybrid_with_chroma(
    student_query: str,
    collection,
    only_doctors: bool = False,
    top_k: int = 10,
    productivity_weight: float = 0.5
):
    """
    Recomenda orientadores usando um score híbrido de similaridade semântica e produtividade.
    """
    # --- 1. Filtro e Busca Semântica no ChromaDB ---
    where_filter = {}
    if only_doctors:
        where_filter = {"tem_doutorado": True}

    # CORREÇÃO: Verificamos se o filtro não está vazio antes de passá-lo para a consulta.
    if where_filter:
        results = collection.query(
            query_texts=[student_query],
            n_results=top_k * 2,
            where=where_filter,
            include=['metadatas', 'distances']
        )
    else:
        # Se não houver filtro, não incluímos o parâmetro 'where' na chamada.
        results = collection.query(
            query_texts=[student_query],
            n_results=top_k * 2,
            include=['metadatas', 'distances']
        )
    
    if not results or not results['ids'][0]:
        return []

    # --- 2. Preparação dos Dados e Cálculo do Score de Produtividade ---
    ids = results['ids'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]

    df = pd.DataFrame(metadatas)
    df['id_pessoa'] = ids
    df['distance'] = distances
    
    df['semantic_similarity'] = 1 - df['distance']
    
    for col in ['publicacoes_count', 'orientacoes_count', 'qualis_score']:
        if df[col].max() > 0:
            df[f'norm_{col}'] = df[col] / df[col].max()
        else:
            df[f'norm_{col}'] = 0
            
    df['productivity_score'] = (
        df['norm_publicacoes_count'] +
        df['norm_orientacoes_count'] +
        df['norm_qualis_score']
    )
    
    if df['productivity_score'].max() > 0:
        df['norm_productivity_score'] = df['productivity_score'] / df['productivity_score'].max()
    else:
        df['norm_productivity_score'] = 0

    # --- 3. Cálculo do Score Híbrido e Re-ranking ---
    df['hybrid_score'] = (
        (df['semantic_similarity'] * (1 - productivity_weight)) +
        (df['norm_productivity_score'] * productivity_weight)
    )

    df_ranked = df.sort_values(by='hybrid_score', ascending=False).head(top_k)

    # --- 4. Formatação da Saída ---
    final_results = []
    for _, row in df_ranked.iterrows():
        final_results.append({
            'id': row['id_pessoa'],
            'nome': row['nome_pessoa'],
            'hybrid_score': row['hybrid_score'],
            'semantic_similarity': row['semantic_similarity'],
            'norm_productivity_score': row['norm_productivity_score'],
            'metadata': {
                'id_pessoa': row['id_pessoa'],
                'nome_pessoa': row['nome_pessoa'],
                'publicacoes_count': int(row['publicacoes_count']),
                'orientacoes_count': int(row['orientacoes_count']),
                'qualis_score': float(row['qualis_score']),
                'areas': row['areas'],
                'tem_doutorado': bool(row['tem_doutorado'])
            }
        })
        
    return final_results

# Bloco para testar o script de forma independente
if __name__ == '__main__':
    try:
        import chromadb
    except ImportError:
        print("Por favor, instale o chromadb: pip install chromadb")
        exit()

    client = chromadb.Client()
    collection_name = "orientadores_academicos_teste"
    
    if collection_name in [c.name for c in client.list_collections()]:
        client.delete_collection(name=collection_name)
    
    collection = client.get_or_create_collection(name=collection_name)

    mock_data = {
        'ids': ["1", "2", "3"],
        'documents': [
            "Pesquisa sobre redes neurais e visão computacional.",
            "Foco em inteligência artificial para o mercado financeiro.",
            "Estudos de bioinformática e análise de genoma com machine learning."
        ],
        'metadatas': [
            {'id_pessoa': "1", 'nome_pessoa': "Dr. Alan Turing", 'publicacoes_count': 50, 'orientacoes_count': 20, 'qualis_score': 85.5, 'areas': "IA", 'tem_doutorado': True},
            {'id_pessoa': "2", 'nome_pessoa': "Dra. Ada Lovelace", 'publicacoes_count': 30, 'orientacoes_count': 15, 'qualis_score': 95.0, 'areas': "IA", 'tem_doutorado': True},
            {'id_pessoa': "3", 'nome_pessoa': "Dr. John von Neumann", 'publicacoes_count': 80, 'orientacoes_count': 30, 'qualis_score': 70.0, 'areas': "Bio", 'tem_doutorado': False}
        ]
    }
    collection.add(**mock_data)

    print(f"Coleção de teste '{collection.name}' populada com {collection.count()} registros.")

    student_query = "Quero usar inteligência artificial para analisar dados de mercado"
    recommendations = recommend_hybrid_with_chroma(student_query, collection, top_k=2)

    print(f"\n--- Recomendações para: '{student_query}' ---")
    import json
    print(json.dumps(recommendations, indent=2))


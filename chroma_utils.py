# chroma_utils.py - Funções para interagir com o banco de dados vetorial ChromaDB
import chromadb
from db_utils import get_professors_data

# --- Configurações do ChromaDB ---
# Vamos usar um cliente persistente, que salva os dados em disco.
# Isso garante que o cache não seja perdido ao reiniciar o app.
CHROMA_PATH = "chroma_db_cache"
COLLECTION_NAME = "professors"

def get_chroma_client():
    """Cria e retorna um cliente ChromaDB persistente."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client

def get_or_create_professors_collection():
    """Obtém ou cria a coleção para armazenar os dados dos professores."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def sync_postgres_to_chroma():
    """
    Busca todos os dados de professores do PostgreSQL e os insere/atualiza
    na coleção do ChromaDB, que funciona como um cache rápido.
    """
    print("Iniciando sincronização: PostgreSQL -> ChromaDB")
    
    # 1. Buscar dados do PostgreSQL
    professors = get_professors_data()
    if not professors:
        print("Nenhum professor encontrado no PostgreSQL para sincronizar.")
        return 0

    collection = get_or_create_professors_collection()
    
    # 2. Limpa a coleção antiga para garantir que dados removidos do Postgres
    #    não permaneçam no cache. (Opcional, mas recomendado para consistência)
    #    Para limpar, deletamos a coleção e criamos de novo.
    client = get_chroma_client()
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        print(f"Limpando coleção antiga '{COLLECTION_NAME}'...")
        client.delete_collection(name=COLLECTION_NAME)
    collection = get_or_create_professors_collection()

    # 3. Prepara os dados para o formato do ChromaDB
    #    IDs devem ser strings.
    ids = [str(p['id']) for p in professors]
    documents = [p['research'] for p in professors]
    metadatas = [{'name': p['name']} for p in professors]

    # 4. Adiciona os dados à coleção
    #    ChromaDB não precisa de embeddings para armazenar documentos.
    #    Usaremos ele como um "document store" rápido.
    if ids:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"Sincronização concluída. {len(ids)} orientadores adicionados ao ChromaDB.")
        return len(ids)
    return 0

def get_all_professors_from_chroma():
    """
    Recupera todos os dados de professores do cache ChromaDB e os formata
    para a função de recomendação.
    """
    collection = get_or_create_professors_collection()
    
    # O método 'get()' sem IDs retorna tudo (com um limite alto)
    results = collection.get(include=["metadatas", "documents"])
    
    if not results or not results['ids']:
        return []

    professors_list = []
    for i in range(len(results['ids'])):
        professors_list.append({
            'id': results['ids'][i],
            'name': results['metadatas'][i]['name'],
            'research': results['documents'][i]
        })
        
    return professors_list

if __name__ == '__main__':
    # Bloco para testar as funções diretamente
    print("--- Testando Sincronização ---")
    try:
        count = sync_postgres_to_chroma()
        print(f"Teste de sincronização finalizado. {count} registros processados.")
        
        if count > 0:
            print("\n--- Testando Leitura do ChromaDB ---")
            professors = get_all_professors_from_chroma()
            if professors:
                print(f"Sucesso! Encontrados {len(professors)} professores no ChromaDB.")
                print("Exemplo do primeiro professor:")
                print(professors[0])
            else:
                print("Falha ao ler dados do ChromaDB após a sincronização.")
    except Exception as e:
        print(f"\nOcorreu um erro durante o teste: {e}")
        print("Verifique se seu banco de dados PostgreSQL está rodando e acessível.")

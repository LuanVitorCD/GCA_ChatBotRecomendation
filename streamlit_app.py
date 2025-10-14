# streamlit_app.py - Interface principal com Streamlit (versão Híbrida Final)
import streamlit as st
import pandas as pd
import traceback
import chromadb

# --- Importando a lógica de recomendação e utilitários ---
from recommend_chroma import recommend_hybrid_with_chroma
from chroma_utils import sync_postgres_to_chroma

# --------------------------------------------------------------------------- #
#                      SETUP DO CHROMA DB (CACHE)                             #
# --------------------------------------------------------------------------- #

@st.cache_resource
def get_chroma_collection():
    """
    Inicializa o cliente PERSISTENTE do ChromaDB e retorna a coleção.
    A função de embedding é gerenciada internamente pelo ChromaDB.
    """
    try:
        client = chromadb.PersistentClient(path="chroma_db_cache")
        collection = client.get_or_create_collection(
            name="orientadores_academicos"
        )
        print("Instância do ChromaDB e coleção carregadas com sucesso.")
        return collection
    except Exception as e:
        st.error(f"Não foi possível inicializar o ChromaDB: {e}")
        return None

# Carrega a coleção uma vez para todo o app
collection = get_chroma_collection()


# --------------------------------------------------------------------------- #
#                   FUNÇÃO PARA EXIBIR OS CARDS DE RESULTADO                  #
# --------------------------------------------------------------------------- #

def display_results_as_cards(results):
    """ Exibe os resultados em um layout de cards expansíveis. """
    st.success(f"Encontramos {len(results)} orientador(es) com alta afinidade:")
    num_cols = len(results) if len(results) <= 3 else 3
    cols = st.columns(num_cols)
    for i, r in enumerate(results):
        with cols[i % num_cols]:
            with st.container(border=True):
                st.markdown(f"#### {r['nome']}")
                st.markdown(f"**Score Híbrido: {r['hybrid_score']:.2f}**")
                st.progress(r['hybrid_score'])
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="Similaridade", value=f"{r['semantic_similarity']:.2f}")
                with col2:
                    st.metric(label="Produtividade", value=f"{r['norm_productivity_score']:.2f}")
                with st.expander("Ver mais detalhes"):
                    meta = r['metadata']
                    st.markdown(f"**ID:** `{meta['id_pessoa']}`")
                    st.markdown(f"**Áreas:** `{meta['areas']}`")
                    # CORREÇÃO: Corrigido o erro de digitação de 'tem_dourado' para 'tem_doutorado'
                    st.markdown(f"**Programa de Doutorado:** {'Sim' if meta.get('tem_doutorado') else 'Não'}")
                    st.divider()
                    st.markdown("**Métricas de Produtividade (originais):**")
                    st.json({
                        "Publicações (contagem)": meta.get('publicacoes_count', 0),
                        "Orientações (contagem)": meta.get('orientacoes_count', 0),
                        "Score Qualis": meta.get('qualis_score', 0)
                    })

# --------------------------------------------------------------------------- #
#                      INTERFACE PRINCIPAL DO STREAMLIT                       #
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="RecomendaProf Híbrido", layout="wide", initial_sidebar_state="expanded")
st.title("🎓 RecomendaProf Híbrido")
st.write("Um sistema de recomendação que combina **similaridade semântica** com **métricas de produtividade acadêmica**.")

st.sidebar.title("Configurações")
only_doctors = st.sidebar.checkbox("Recomendar apenas orientadores de programas de Doutorado")

st.sidebar.title("Gerenciamento de Dados")
st.sidebar.write("Sincronize os dados do PostgreSQL para o cache local (ChromaDB).")

if st.sidebar.button("Sincronizar PostgreSQL ➔ ChromaDB"):
    if collection is None:
        st.sidebar.error("ChromaDB não foi inicializado. Verifique os logs.")
    else:
        try:
            with st.spinner("Buscando dados do PostgreSQL e salvando no ChromaDB..."):
                count = sync_postgres_to_chroma(collection)
            st.sidebar.success(f"{count} orientador(es) sincronizados com sucesso!")
            st.toast("Sincronização concluída!", icon="✅")
        except Exception as e:
            st.sidebar.error("Falha na sincronização.")
            st.toast("Erro ao sincronizar.", icon="❌")
            st.error(f"Detalhes do erro de sincronização: {e}")

st.header("Qual é o seu interesse de pesquisa?")
student_area = st.text_input("Palavras-chave (ex: inteligência artificial, redes neurais):", "Redes neurais para imagens médicas")
student_text_details = st.text_area("Descreva com mais detalhes seu projeto:", "Meu foco é usar deep learning para detectar anomalias em ressonância magnética.", height=100)

if st.button("Recomender Orientadores"):
    if not student_area and not student_text_details:
        st.error("Por favor, descreva sua área de pesquisa.")
    elif collection is None:
        st.error("A conexão com o ChromaDB falhou. Verifique o console.")
    elif collection.count() == 0:
        st.warning("Nenhum orientador no cache. Sincronize os dados na barra lateral.")
    else:
        full_query = f"{student_area}. {student_text_details}"
        with st.spinner("Buscando e ranqueando os melhores orientadores..."):
            try:
                results = recommend_hybrid_with_chroma(
                    student_query=full_query,
                    collection=collection,
                    only_doctors=only_doctors,
                    top_k=5
                )
                st.header("Resultados da Recomendação")
                if results:
                    display_results_as_cards(results)
                else:
                    st.warning("Nenhum orientador com afinidade suficiente foi encontrado.")
            except Exception:
                st.error("Ocorreu um erro durante a recomendação.")
                with st.expander("Detalhes do Erro"):
                    st.code(traceback.format_exc())


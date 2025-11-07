# streamlit_app.py - Interface principal com Streamlit (versão com UI aprimorada)
import streamlit as st
import pandas as pd
import traceback
import chromadb

# --- Importando a lógica de recomendação e utilitários ---
from recommend_chroma import recommend_hybrid_with_chroma
from chroma_utils import sync_postgres_to_chroma
from db_utils import get_publications_by_professor_id

# --- IMPORTANDO O NOVO MOTOR LEGADO ---
from recommend_legacy import recommend_legacy_clustering

# --------------------------------------------------------------------------- #
#                      SETUP DO CHROMA DB (CACHE)                             #
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_chroma_collection():
    """
    Inicializa o cliente PERSISTENTE do ChromaDB e retorna a coleção.
    """
    try:
        client = chromadb.PersistentClient(path="chroma_db_cache")
        collection = client.get_or_create_collection(name="orientadores_academicos")
        print("Instância do ChromaDB e coleção carregadas com sucesso.")
        return collection
    except Exception as e:
        st.error(f"Não foi possível inicializar o ChromaDB: {e}")
        return None

collection = get_chroma_collection()


# --------------------------------------------------------------------------- #
#             FUNÇÃO PARA APLICAR TEMA CUSTOMIZADO (PRETO E AZUL)             #
# --------------------------------------------------------------------------- #
def set_custom_theme():
    st.markdown("""
        <style>
            /* -------------------- GERAL -------------------- */
            .stApp, .stMarkdown, label, p, span {
                color: #E0E0E0 !important;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF !important;
            }

            /* -------------------- CHECKBOX -------------------- */
            div[data-baseweb="checkbox"] svg {
                fill: #4b67ff !important;      /* marca interna */
                stroke: #4b67ff !important;
            }
            div[data-baseweb="checkbox"] > div:first-child {
                border: 2px solid #4b67ff !important; /* borda do quadrado */
                border-radius: 4px !important;
            }

            /* -------------------- RADIO -------------------- */
            .stApp label[data-baseweb="radio"] > div > label[data-baseweb="radio"] > div {
                background-color: #4b67ff !important;
                border: 2px solid #4b67ff !important;
            }

            /* -------------------- TOGGLE -------------------- */
            div[data-testid="stToggle"] div[role="switch"] {
                background-color: #4b67ff !important;  /* cor do fundo ligado */
                border: 1px solid #4b67ff !important;
            }
            div[data-testid="stToggle"] div[role="switch"] div {
                background-color: white !important;    /* bolinha branca */
            }

            /* -------------------- SLIDER -------------------- */
            div[data-baseweb="slider"] > div:nth-child(2) {
                background-color: #333 !important;     /* trilha vazia */
            }
            div[data-baseweb="slider"] > div:nth-child(3),
            div[data-baseweb="slider"] > div:nth-child(4) {
                background-color: #4b67ff !important;  /* trilha cheia */
            }
            div[data-baseweb="slider"] [role="slider"] {
                background-color: #4b67ff !important;  /* knob (ponto) */
                border: 2px solid #4b67ff !important;
                box-shadow: 0 0 6px #4b67ff !important;
            }

            /* -------------------- BOTÕES -------------------- */
            button {
                border-radius: 6px !important;
                border: 1px solid #4b67ff !important;
                background-color: transparent !important;
                color: #4b67ff !important;
                transition: all 0.2s ease-in-out !important;
            }
            button:hover {
                background-color: #4b67ff !important;
                color: white !important;
            }
            button[kind="primary"] {
                background-color: #4b67ff !important;
                color: white !important;
            }
            button[kind="primary"]:hover {
                background-color: #3b55cc !important;
            }

            /* -------------------- PROGRESS BAR -------------------- */
            .stProgress > div > div > div > div {
                background-color: #4b67ff !important;
            }

            /* -------------------- SIDEBAR -------------------- */
            section[data-testid="stSidebar"] {
                background-color: #14161A !important;
                border-right: 1px solid #2A2A3C !important;
            }

            /* -------------------- CONTAINERS -------------------- */
            [data-testid="stContainer"], .stContainer {
                background-color: #1E1E2E !important;
                border: 1px solid #333 !important;
                border-radius: 10px !important;
            }
        </style>
    """, unsafe_allow_html=True)







# --------------------------------------------------------------------------- #
#       FUNÇÃO PARA EXIBIR OS CARDS DE RESULTADO (NOVO DESIGN)                #
# --------------------------------------------------------------------------- #
def display_results_as_cards(results, publication_limit):
    """ Exibe os resultados em um layout de cards mais elaborado e com dropdown de publicações. """
    st.header("⭐ Orientadores Recomendados (Moderno)")
    st.markdown("Abaixo estão os professores com maior afinidade com seu tema de pesquisa.")

    num_cols = min(len(results), 3)
    cols = st.columns(num_cols)

    for i, r in enumerate(results):
        with cols[i % num_cols]:
            with st.container(border=True):
                st.subheader(f"{r['nome']}")
                st.markdown(f"**Score de Afinidade: {r['hybrid_score']:.2f}**")
                st.progress(float(r['hybrid_score']))
                st.divider()

                col1, col2 = st.columns(2)
                col1.metric(label="Similaridade", value=f"{r['semantic_similarity']:.2f}")
                col2.metric(label="Produtividade", value=f"{r['norm_productivity_score']:.2f}")

                meta = r['metadata']

                with st.expander("Ver mais detalhes"):
                    # CORREÇÃO: Usa 'Não informado' como padrão se a área estiver vazia
                    areas_display = meta.get('areas') if meta.get('areas') else "Não informado"
                    st.markdown(f"**Áreas de Conhecimento:** `{areas_display}`")
                    
                    status_doutorado = "Sim" if meta.get('tem_doutorado') else "Não"
                    st.markdown(f"**Vinculado a Doutorado:** {status_doutorado}")
                    st.json({
                        "Publicações (total)": meta.get('publicacoes_count', 0),
                        "Orientações (total)": meta.get('orientacoes_count', 0),
                        "Score Qualis (médio)": round(meta.get('qualis_score', 0), 2)
                    })
                
                with st.expander("Ver publicações"):
                    # A busca de publicações é específica do ChromaDB, 
                    # então desabilitamos para o legado ou buscamos de forma diferente
                    with st.spinner("Buscando publicações..."):
                        publications, total_count = get_publications_by_professor_id(r['id'], limit=publication_limit)
                    
                    if publications:
                        for pub in publications:
                            st.markdown(f"- _{pub}_")
                        
                        if total_count > len(publications):
                            st.info(f"Mostrando {len(publications)} de {total_count} publicações.")
                    else:
                        st.info("Nenhuma publicação encontrada.")

# --------------------------------------------------------------------------- #
#                      INTERFACE PRINCIPAL DO STREAMLIT                       #
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="RecomendaProf", layout="wide", initial_sidebar_state="expanded")
set_custom_theme()

st.title("RecomendaProf")
st.markdown("Encontre o orientador ideal para sua pesquisa. Nosso sistema combina a **similaridade semântica** do seu projeto com as **métricas de produtividade acadêmica** dos professores.")
st.divider()

with st.sidebar:
    st.title("Configurações")
    
    # --- NOVO: SELETOR DE MOTOR ---
    st.subheader("Motor de Recomendação")
    recommendation_mode = st.radio(
        "Selecione o motor para a recomendação:",
        ("Moderno (Vetorial)", "Legado (Clustering)"),
        help="Vetorial: Usa ChromaDB para busca semântica (rápido). Clustering: Usa a lógica original de clustering e SQL (lento)."
    )
    st.divider()
    
    st.subheader("Filtros")
    only_doctors = st.checkbox("Apenas de programas com Doutorado", value=True)
    top_k_slider = st.slider("Número de recomendações", min_value=3, max_value=9, value=3)
    
    # Slider de publicações com opção "Todas"
    max_pubs_slider = st.slider("Máx. de publicações por orientador", min_value=1, max_value=51, value=5)
    if max_pubs_slider == 51:
        max_pubs_limit = None
        st.caption("Exibindo: Todas as publicações")
    else:
        max_pubs_limit = max_pubs_slider
        st.caption(f"Exibindo: Até {max_pubs_slider} publicações")


    st.divider()
    st.title("Gerência de Dados")
    st.write("Sincronize os dados do PostgreSQL para o cache local (ChromaDB).")
    if st.button("Sincronizar Dados", use_container_width=True):
        if collection is None:
            st.error("ChromaDB não inicializado.")
        else:
            try:
                with st.spinner("Sincronizando..."):
                    count = sync_postgres_to_chroma(collection)
                st.success(f"{count} orientador(es) sincronizados!")
                st.toast("Sincronização concluída!", icon="✅")
            except Exception as e:
                st.error("Falha na sincronização.")
                st.toast("Erro ao sincronizar.", icon="❌")

st.header("🔍 Descreva sua Pesquisa")
student_area = st.text_input(
    "**Palavras-chave:**", "Redes neurais para imagens médicas", help="Termos principais da sua pesquisa."
)
student_text_details = st.text_area(
    "**Detalhes do Projeto:**", "Meu foco é usar deep learning para detectar anomalias em ressonância magnética.",
    height=120, help="Descreva seu projeto com mais detalhes para uma recomendação mais precisa."
)

if st.button("Encontrar Orientador Ideal", use_container_width=True, type="primary"):
    if not student_area and not student_text_details:
        st.error("Por favor, descreva sua área de pesquisa.")
    else:
        full_query = f"{student_area}. {student_text_details}"

        # --- MODIFICADO: Confirmação dos Termos de Busca ---
        with st.container(border=True):
            st.markdown(f"**Buscando recomendações com base em:**")
            st.caption(full_query)
        st.divider()


        # --- LÓGICA DE SELEÇÃO DE MOTOR ---
        if recommendation_mode == "Moderno (Vetorial)":
            if collection is None:
                st.error("A conexão com o ChromaDB falhou. Verifique o console.")
            elif collection.count() == 0:
                st.warning("Nenhum orientador no cache. Sincronize os dados na barra lateral.")
            else:
                with st.spinner("Buscando e ranqueando (Motor Moderno)..."):
                    try:
                        results = recommend_hybrid_with_chroma(
                            student_query=full_query, collection=collection,
                            only_doctors=only_doctors, top_k=top_k_slider
                        )
                        st.divider()
                        if results:
                            display_results_as_cards(results, max_pubs_limit)
                        else:
                            st.warning("Nenhum orientador com afinidade suficiente foi encontrado.")
                    except Exception:
                        st.error("Ocorreu um erro durante a recomendação moderna.")
                        with st.expander("Detalhes do Erro"):
                            st.code(traceback.format_exc())
        
        elif recommendation_mode == "Legado (Clustering)":
            st.info("Executando o motor legado (Clustering + SQL). Isso pode demorar vários segundos...")
            with st.spinner("Buscando, clusterizando e ranqueando (Motor Legado)..."):
                try:
                    legacy_results_str = recommend_legacy_clustering(full_query, only_doctors)
                    st.divider()
                    st.header("⭐ Orientadores Recomendados (Legado)")
                    st.text_area("Resultados", legacy_results_str, height=300)
                
                except ImportError:
                    st.error("Erro: O motor legado requer 'spacy'.")
                    st.code("pip install spacy")
                    st.code("python -m spacy download pt_core_news_md")
                except Exception:
                    st.error("Ocorreu um erro durante a recomendação legada.")
                    with st.expander("Detalhes do Erro"):
                        st.code(traceback.format_exc())
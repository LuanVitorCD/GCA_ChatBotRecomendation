# streamlit_app.py - Interface principal com Streamlit
import streamlit as st
import pandas as pd
import traceback
import chromadb

# --- Importando a lógica de recomendação e utilitários ---
from recommend_chroma import recommend_hybrid_with_chroma
from chroma_utils import sync_postgres_to_chroma
from db_utils import get_publications_by_professor_id

# --- MOTOR LEGADO ---
from recommend_legacy import recommend_legacy_clustering

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

def parse_legacy_results(legacy_string: str) -> list:
    """
    Converte a string de resultado do motor legado em uma lista de
    dicionários compatível com os cards.
    """
    results = []
    if "Nenhum orientador" in legacy_string:
        return []
    
    lines = legacy_string.strip().split('\n\n')
    for line in lines:
        parts = line.split(' - Rating: ')
        if len(parts) == 2:
            nome = parts[0]
            score = float(parts[1])
            results.append({
                'nome': nome,
                'hybrid_score': score,
                # ID Fictício para o botão de feedback.
                # Cuidado: Nomes duplicados podem causar colisões de chave.
                'id': f"legacy_{nome.replace(' ', '_').lower()}",
                'metadata': {}, # Motor legado não fornece metadados ricos
                'semantic_similarity': 0.0,
                'norm_productivity_score': score # No legado, o score é só produtividade
            })
    return results

def display_results_as_cards(results: list, publication_limit: int, engine: str = "Moderno", query_text: str = ""):
    """ 
    Exibe os resultados em cards, com:
    1. Badge do motor (legado/moderno)
    2. XAI (Explainable AI) para o motor moderno
    3. Botões de Feedback
    4. Compatibilidade com dados do motor legado
    """
    st.markdown(f"**Resultados (Motor {engine}):**")

    num_cols = min(len(results), 3)
    cols = st.columns(num_cols)

    for i, r in enumerate(results):
        with cols[i % num_cols]:
            with st.container(border=True):
                st.subheader(f"{r['nome']}")
                st.caption(f"Gerado por: Motor {engine}") # Badge
                
                st.markdown(f"**Score de Afinidade: {r['hybrid_score']:.2f}**")
                
                if engine == "Moderno":
                    st.progress(float(r['hybrid_score']))
                
                # --- Explainable AI (XAI) ---
                if engine == "Moderno":
                    similarity = r.get('semantic_similarity', 0)
                    productivity = r.get('norm_productivity_score', 0)
                    
                    if similarity > 0.6 and productivity > 0.6:
                        st.success("Recomendação forte: alta afinidade de pesquisa e excelente produtividade.")
                    elif similarity > 0.6:
                        st.info("Recomendação com alta afinidade de pesquisa (tema muito parecido).")
                    elif productivity > 0.6:
                        st.info("Recomendação com alta produtividade (muitas publicações e orientações).")

                st.divider()

                col1, col2 = st.columns(2)
                # Usar .get() garante compatibilidade com o legado
                col1.metric(label="Similaridade", value=f"{r.get('semantic_similarity', 0.0):.2f}")
                col2.metric(label="Produtividade", value=f"{r.get('norm_productivity_score', 0.0):.2f}")

                # --- Paridade Visual (Lógica de Detalhes) ---
                if engine == "Moderno":
                    meta = r.get('metadata', {})
                    
                    with st.expander("Ver mais detalhes"):
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
                        with st.spinner("Buscando..."):
                            publications, total_count = get_publications_by_professor_id(r['id'], limit=publication_limit)
                        
                        if publications:
                            for pub in publications:
                                st.markdown(f"- _{pub}_")
                            if total_count > len(publications):
                                st.info(f"Mostrando {len(publications)} de {total_count} publicações.")
                        else:
                            st.info("Nenhuma publicação encontrada.")
                else:
                    st.info("Detalhes e publicações não estão disponíveis para o motor legado.")
                
                # --- Loop de Feedback ---
                st.divider()
                col_up, col_down = st.columns(2)
                
                # Chaves únicas para os botões
                key_up = f"up_{r['id']}_{query_text}"
                key_down = f"down_{r['id']}_{query_text}"
                
                if col_up.button("👍 Relevante", use_container_width=True, key=key_up):
                    st.toast(f"Feedback salvo: {r['nome']}!", icon="✅")
                    # Em um app real, aqui você salvaria no DB/log:
                    # log_feedback(r['id'], 'up', engine, query_text)
                
                if col_down.button("👎 Pouco relevante", use_container_width=True, key=key_down):
                    st.toast(f"Feedback salvo: {r['nome']}.", icon="❌")
                    # log_feedback(r['id'], 'down', engine, query_text)

st.set_page_config(page_title="RecomendaProf", layout="wide", initial_sidebar_state="expanded")
set_custom_theme()

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configurações")
    
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
    
    max_pubs_slider = st.slider("Máx. de publicações por orientador", min_value=1, max_value=51, value=5)
    if max_pubs_slider == 51:
        max_pubs_limit = None
        st.caption("Exibindo: Todas as publicações")
    else:
        max_pubs_limit = max_pubs_slider
        st.caption(f"Exibindo: Até {max_pubs_slider} publicações")

    # Botão para limpar chat
    st.divider()
    if st.button("🗑️ Limpar Histórico", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.title("🔄 Gerência de Dados")
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

# --- ÁREA PRINCIPAL (UI DE CHATBOT) ---
st.title("🎓 RecomendaProf")
st.markdown("Encontre o orientador ideal para sua pesquisa. Esta interface de chat irá guiar você.")
st.divider()

# Inicializa o histórico de chat no session_state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Lógica para re-exibir os cards ou texto
        if message["type"] == "cards":
            display_results_as_cards(
                message["content"], 
                max_pubs_limit, 
                message["engine"], 
                message["query"]
            )
        else:
            st.markdown(message["content"])

# Input do usuário (st.chat_input)
if prompt := st.chat_input("Descreva sua área de pesquisa (ex: 'deep learning para imagens médicas')"):
    # Adiciona a mensagem do usuário ao histórico e exibe
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Processa a recomendação como "assistant"
    with st.chat_message("assistant"):
        full_query = prompt
        
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
                        
                        if results:
                            # Exibe os cards e salva no histórico
                            display_results_as_cards(results, max_pubs_limit, "Moderno", full_query)
                            st.session_state.messages.append({
                                "role": "assistant", "type": "cards", 
                                "content": results, "engine": "Moderno", "query": full_query
                            })
                        else:
                            st.warning("Nenhum orientador com afinidade suficiente foi encontrado.")
                            st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Nenhum orientador com afinidade suficiente foi encontrado."})
                        
                    except Exception:
                        st.error("Ocorreu um erro durante a recomendação moderna.")
                        with st.expander("Detalhes do Erro"):
                            st.code(traceback.format_exc())
        
        elif recommendation_mode == "Legado (Clustering)":
            st.info("Executando o motor legado (Clustering + SQL). Isso pode demorar...")
            with st.spinner("Buscando, clusterizando e ranqueando (Motor Legado)..."):
                try:
                    legacy_results_str = recommend_legacy_clustering(full_query, only_doctors)
                    legacy_results_list = parse_legacy_results(legacy_results_str)
                    
                    if legacy_results_list:
                        # Exibe os cards e salva no histórico
                        display_results_as_cards(legacy_results_list, max_pubs_limit, "Legado", full_query)
                        st.session_state.messages.append({
                            "role": "assistant", "type": "cards", 
                            "content": legacy_results_list, "engine": "Legado", "query": full_query
                        })
                    else:
                        st.warning("Nenhum orientador foi encontrado pelo motor legado.")
                        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Nenhum orientador foi encontrado pelo motor legado."})
                
                except ImportError:
                    st.error("Erro: O motor legado requer 'spacy'.")
                    st.code("pip install spacy && python -m spacy download pt_core_news_md")
                except Exception:
                    st.error("Ocorreu um erro durante a recomendação legada.")
                    with st.expander("Detalhes do Erro"):
                        st.code(traceback.format_exc())
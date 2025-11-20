# streamlit_app.py - Interface Final com Pivô para Motor Legado, LLM e Sync de Dados
import streamlit as st
import pandas as pd
import traceback
import time
import requests
import json
import random
import chromadb

# Lógica de recomendação
from recommend_legacy import recommend_legacy_clustering
from db_utils import get_publications_by_professor_id

# Utilitários do ChromaDB
from chroma_utils import sync_postgres_to_chroma

# Configuração da página
st.set_page_config(page_title="RecomendaProf - Tese", layout="wide", initial_sidebar_state="expanded")



# Função para aplicar tema customizado CSS
def set_custom_theme():
    st.markdown("""
        <style>
            /* Cores Gerais */
            .stApp, .stMarkdown, label, p, span, h1, h2, h3, h4, h5, h6 { 
                color: #E0E0E0 !important; 
            }
            
            /* Botões Primários (Favoritar/Ação) */
            button[kind="primary"] {
                background-color: #4b67ff !important;
                color: white !important;
                border: none;
                transition: 0.3s;
            }
            button[kind="primary"]:hover {
                background-color: #3b55cc !important;
                box-shadow: 0 0 10px rgba(75, 103, 255, 0.5);
            }

            /* Alinhamento de Botões na Coluna Direita */
            div[data-testid="column"] button {
                width: 100%;
                margin-bottom: 5px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            /* Ajuste sutil para separar o conteúdo */
            hr { margin: 1.5em 0; border-color: #333; }
        </style>
    """, unsafe_allow_html=True)

set_custom_theme()



# Setup para sincronização com ChromaDB
@st.cache_resource
def get_chroma_collection():
    """ Inicializa o cliente para permitir a sincronização dos dados """
    try:
        client = chromadb.PersistentClient(path="chroma_db_cache")
        collection = client.get_or_create_collection(name="orientadores_academicos")
        return collection
    except Exception as e:
        print(f"Aviso: ChromaDB não inicializado (apenas necessário para sync): {e}")
        return None

collection = get_chroma_collection()



# Gerenciamento de estados
if 'favorites' not in st.session_state:
    st.session_state.favorites = {} 
if 'blacklist' not in st.session_state:
    st.session_state.blacklist = {} 
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = []
if 'refined_query' not in st.session_state:
    st.session_state.refined_query = ""
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "search" 
if 'selected_prof' not in st.session_state:
    st.session_state.selected_prof = None



# Integração com LLMs
def call_ollama(prompt, model="mistral"):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.7} 
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Erro ao conectar com Ollama: {e}"

def call_gemini(prompt, api_key):
    return "Integração Gemini ainda não configurada."

def llm_refine_query(user_text, provider, model_name, api_key=None):
    system_prompt = (
        f"Atue como um assistente acadêmico especialista. "
        f"O usuário vai descrever um tema de pesquisa. "
        f"Converta isso para 3 a 5 palavras-chave técnicas acadêmicas (Lattes). "
        f"Retorne APENAS as palavras separadas por espaço.\n\n"
        f"Texto: '{user_text}'"
    )
    
    if provider == "Simulação":
        refinement = user_text
        keywords = ["pesquisa", "desenvolvimento", "tecnologia", "análise", "estudo"]
        if len(user_text.split()) < 4:
            refinement += " " + " ".join(keywords[:2])
        return refinement
        
    elif provider == "Local (Ollama)":
        return call_ollama(system_prompt, model=model_name)
    elif provider == "Gemini (API)":
        return call_gemini(system_prompt, api_key)
    return user_text

def llm_explain_recommendation(prof_name, score, user_query, provider, model_name, api_key=None):
    prompt = (
        f"Escreva uma justificativa curta (máximo 2 frases) explicando por que o professor '{prof_name}' "
        f"é uma boa recomendação para o tema '{user_query}'. "
        f"O algoritmo deu um score de {score:.2f}. Seja profissional."
    )
    
    if provider == "Simulação":
        templates = [
            f"Com base na busca por '{user_query}', o algoritmo identificou **{prof_name}** como forte correspondência (Score: {score:.2f}).",
            f"A trajetória acadêmica de **{prof_name}** apresenta alta sinergia com o tema '{user_query}', refletida no índice {score:.2f}.",
            f"Para o tema '{user_query}', **{prof_name}** destaca-se pela produtividade e experiência na área (Índice: {score:.2f})."
        ]
        random.seed(prof_name + user_query) 
        return random.choice(templates)
        
    elif provider == "Local (Ollama)":
        return call_ollama(prompt, model=model_name)
    return "Explicação indisponível."



# Parser e lógicas auxiliares
def parse_legacy_results(legacy_string):
    results = []
    if "Nenhum orientador" in legacy_string:
        return []
    lines = legacy_string.strip().split('\n\n')
    for line in lines:
        parts = line.split(' - Rating: ')
        if len(parts) == 2:
            nome = parts[0]
            try: score = float(parts[1])
            except: score = 0.0
            id_ficticio = nome.replace(" ", "_").lower()
            
            if id_ficticio not in st.session_state.blacklist:
                results.append({'nome': nome, 'hybrid_score': score, 'id': id_ficticio})
    return results

def toggle_favorite(prof):
    prof_id = prof['id']
    if prof_id in st.session_state.favorites:
        del st.session_state.favorites[prof_id]
        st.toast(f"Removido dos favoritos.", icon="🗑️")
    else:
        if prof_id in st.session_state.blacklist:
            del st.session_state.blacklist[prof_id]
        st.session_state.favorites[prof_id] = prof 
        st.toast(f"Favoritado!", icon="⭐")

def toggle_blacklist(prof):
    prof_id = prof['id']
    if prof_id in st.session_state.blacklist:
        del st.session_state.blacklist[prof_id]
        st.toast(f"Restaurado.", icon="👁️")
    else:
        if prof_id in st.session_state.favorites:
            del st.session_state.favorites[prof_id]
        st.session_state.blacklist[prof_id] = prof
        st.toast(f"Ocultado.", icon="🚫")
        st.session_state.current_results = [p for p in st.session_state.current_results if p['id'] != prof_id]

def clear_search():
    st.session_state.current_results = []
    st.session_state.refined_query = ""
    st.session_state.view_mode = "search"
    st.rerun()

def view_professor_details(prof):
    st.session_state.selected_prof = prof
    st.session_state.view_mode = "single_view"
    st.rerun()

def back_to_search():
    st.session_state.view_mode = "search"
    st.session_state.selected_prof = None
    st.rerun()



# INTERFACE LATERAL #
with st.sidebar:
    st.title("🎓 RecomendaProf")
    st.caption("Baseado na Tese de Doutorado de Radi Melo Martins")
    
    st.divider()
    st.subheader("🧠 Configuração da IA")
    llm_provider = st.selectbox("Provedor de Inteligência:", ["Simulação", "Local (Ollama)", "Gemini (API)"])
    
    ollama_model = "mistral"
    api_key = None
    if llm_provider == "Local (Ollama)":
        ollama_model = st.text_input("Modelo Ollama:", value="mistral")
    elif llm_provider == "Gemini (API)":
        api_key = st.text_input("API Key do Google:", type="password")

    st.divider()
    st.subheader("Filtros & Limites")
    only_doctors = st.checkbox("Apenas Doutorado", value=True)
    max_professors = st.slider("Máx. Professores", 1, 20, 5)
    max_pubs_limit = st.slider("Máx. Publicações", 1, 10, 3)

    st.divider()
    
    st.subheader(f"⭐ Favoritos ({len(st.session_state.favorites)})")
    if st.session_state.favorites:
        for fav_id, fav_data in list(st.session_state.favorites.items()):
            c1, c2 = st.columns([4, 1])
            if c1.button(fav_data['nome'], key=f"nav_fav_{fav_id}"):
                view_professor_details(fav_data)
            if c2.button("✕", key=f"rm_fav_{fav_id}"):
                 del st.session_state.favorites[fav_id]
                 st.rerun()
    else:
        st.caption("Nenhum favorito ainda.")

    st.divider()
    if st.session_state.blacklist:
        with st.expander(f"🚫 Ocultados ({len(st.session_state.blacklist)})"):
             for black_id, black_data in list(st.session_state.blacklist.items()):
                c1, c2 = st.columns([4, 1])
                c1.text(black_data['nome'])
                if c2.button("↺", key=f"rst_{black_id}"):
                    del st.session_state.blacklist[black_id]
                    st.rerun()

    # Botão para sincronizar dados entre BDs
    st.divider()
    st.markdown("### 🔄 Dados")
    st.caption("Sincronização PostgreSQL -> ChromaDB (Opcional)")
    if st.button("Sincronizar Banco", use_container_width=True):
        if collection is None:
            st.error("ChromaDB não inicializado.")
        else:
            try:
                with st.spinner("Lendo do PostgreSQL e vetorizando..."):
                    count = sync_postgres_to_chroma(collection)
                st.success(f"{count} perfis sincronizados com sucesso!")
            except Exception as e:
                st.error("Falha na sincronização.")
                st.code(str(e))



# INTERFACE PRINCIPAL #
st.title("Encontre seu Orientador Ideal")

# Detalhes
if st.session_state.view_mode == "single_view" and st.session_state.selected_prof:
    prof = st.session_state.selected_prof
    
    if st.button("← Voltar para a busca"):
        back_to_search()
        
    with st.container(border=True):
        st.header(prof['nome'])
        st.caption(f"Índice de Recomendação: **{prof['hybrid_score']:.2f}**")
        
        query_context = st.session_state.refined_query if st.session_state.refined_query else "sua pesquisa"
        explanation = llm_explain_recommendation(prof['nome'], prof['hybrid_score'], query_context, llm_provider, ollama_model, api_key)
        st.info(explanation)
        
        st.subheader("Publicações Detalhadas")
        pubs, total = get_publications_by_professor_id(prof['id'], limit=10)
        if pubs:
            st.write(f"Mostrando as 10 mais recentes de {total} encontradas:")
            for p in pubs: st.markdown(f"- {p}")
        else:
            st.warning("Nenhuma publicação encontrada no banco de dados.")
            
    c1, c2 = st.columns(2)
    is_fav = prof['id'] in st.session_state.favorites
    if c1.button("★ Remover Favorito" if is_fav else "☆ Favoritar", key="det_fav", use_container_width=True, type="primary" if is_fav else "secondary"):
        toggle_favorite(prof)
        st.rerun()
    if c2.button("🚫 Ocultar Professor", key="det_blk", use_container_width=True):
        toggle_blacklist(prof)
        back_to_search()



# Modo de busca padrão
else:
    if st.session_state.search_history:
        with st.expander("Ver histórico da conversa", expanded=False):
            for msg in st.session_state.search_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    if prompt := st.chat_input("Ex: Quero pesquisar sobre uso de machine learning na detecção de câncer..."):
        st.session_state.search_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.status("🧠 Processando...", expanded=True) as status:
            st.write(f"Refinando busca com {llm_provider}...")
            refined_query = llm_refine_query(prompt, llm_provider, ollama_model, api_key)
            st.session_state.refined_query = refined_query
            st.write(f"🔍 Termos gerados: *'{refined_query}'*")
            
            try:
                legacy_raw = recommend_legacy_clustering(refined_query, only_doctors)
                parsed_results = parse_legacy_results(legacy_raw)
                st.session_state.current_results = parsed_results
                status.update(label="Busca concluída!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Erro na busca", state="error")
                st.error(f"Erro no motor legado: {e}")
                st.session_state.current_results = []

    if st.session_state.current_results:
        col_res_1, col_res_2 = st.columns([5, 1])
        results_to_show = st.session_state.current_results[:max_professors]
        col_res_1.subheader(f"Resultados ({len(results_to_show)})")
        if col_res_2.button("Limpar Busca", type="secondary"):
            clear_search()

        st.markdown(f"Baseado nos termos: *{st.session_state.refined_query}*")
        
        for prof in results_to_show:
            is_fav = prof['id'] in st.session_state.favorites
            fav_label = "★ Favorito" if is_fav else "☆ Favoritar"
            fav_type = "primary" if is_fav else "secondary"

            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.markdown(f"### {prof['nome']}")
                    st.caption(f"Índice de Recomendação: **{prof['hybrid_score']:.2f}**")
                    
                    if 'refined_query' in st.session_state:
                         explanation = llm_explain_recommendation(prof['nome'], prof['hybrid_score'], st.session_state.refined_query, llm_provider, ollama_model, api_key)
                         st.info(explanation)

                    with st.expander("Ver publicações recentes"):
                        pubs, _ = get_publications_by_professor_id(prof['id'], limit=max_pubs_limit)
                        if pubs:
                            for p in pubs: st.text(f"• {p}")
                        else:
                            st.caption("Nenhuma publicação encontrada.")

                with c2:
                    st.write("") 
                    if st.button(fav_label, key=f"btn_fav_{prof['id']}", type=fav_type, use_container_width=True):
                        toggle_favorite(prof)
                        st.rerun()
                    
                    if st.button("🚫 Ocultar", key=f"btn_blk_{prof['id']}", use_container_width=True):
                        toggle_blacklist(prof)
                        st.rerun()
                    
                    if st.button("📄 Detalhes", key=f"btn_det_{prof['id']}", use_container_width=True):
                        view_professor_details(prof)

    elif st.session_state.search_history and not st.session_state.current_results:
         st.info("Faça uma nova busca para ver resultados.")
# streamlit_app.py - Interface Final (Otimizada + Caching + UI Moderna)
# Referência: Implementação Computacional da Tese de Radi Melo Martins (2025)
# Contexto: Ferramenta de Validação para a Seção 6 do Artigo.

import streamlit as st
import requests
import json
import random
import traceback
import os
import time
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Configurações de Ambiente ---
# Desativa o handler de erro do Fortran para evitar crash com CTRL+C
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

# --- Imports da Lógica de Negócio ---
from utils.thesis_recommend import thesis_recommendation_engine
from utils.db_utils import get_publications_by_professor_id

# --- Configuração da Página ---
st.set_page_config(
    page_title="RecomendaProf - Validação (Seção 6)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------------------------- #
#                       ESTILIZAÇÃO (CSS PERSONALIZADO)                       #
# --------------------------------------------------------------------------- #
def set_custom_theme():
    st.markdown("""
        <style>
            /* --- Cores e Tipografia --- */
            .stApp { background-color: #0E1117; }
            h1, h2, h3 { color: #FFFFFF !important; font-family: 'Helvetica Neue', sans-serif; }
            p, label, span { color: #E0E0E0 !important; }
            
            /* --- Botões --- */
            button[kind="primary"] { 
                background-color: #4b67ff !important; 
                color: white !important; 
                border-radius: 8px;
                border: none; 
                transition: all 0.3s ease;
            }
            button[kind="primary"]:hover {
                background-color: #3b55cc !important;
                box-shadow: 0 4px 12px rgba(75, 103, 255, 0.4);
                transform: translateY(-1px);
            }
            button[kind="secondary"] {
                border-radius: 8px;
                border: 1px solid #4b67ff;
            }
            button[kind="tertiary"] {
                padding: 0.5rem 1rem;
                border-radius: 8px;
                border: 1px solid #4b67ff;
                color: white !important; 
                transition: all 0.3s ease;
                overflow: hidden;
                white-space: nowrap;
                display: block;
                text-overflow: ellipsis;    
            }
            button[kind="tertiary"]:hover {
                border-radius: 8px;
                border: 1px solid #4b67ff;
                background: #1e1e2e !important;
                box-shadow: 0 4px 12px rgba(75, 103, 255, 0.4);
                transform: translateY(-1px);
                overflow: hidden;
                white-space: nowrap;
                display: block;
                text-overflow: ellipsis;    
            }
            /* --- Cards de Resultados --- */
            div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #1e1e2e;
                border-radius: 12px;
                padding: 15px;
                border: 1px solid #333;
                transition: border-color 0.3s;
            }
            div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                border-color: #4b67ff;
            }
            /* --- Score Breakdown --- */
            .score-container {
                background: #252535;
                padding: 10px;
                border-radius: 8px;
                border-left: 4px solid #4b67ff;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            /* --- Métricas Simples --- */
            .metric-label {
                font-size: 0.75rem;
                color: #bbb;
                text-transform:
                uppercase;
                letter-spacing: 0.5px;
            }
            .metric-value {
                font-size: 1.1rem;
                color: #fff;
                font-weight: bold;
            }
            /* --- Box de Informações Acadêmicas --- */
            .academic-info-box {
                background-color: #1a1c24;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .info-label {
                font-weight: bold;
                color: #4b67ff !important;
            } 
            /* --- Cards de Métricas --- */
            .metric-container {
                display: grid;
                grid-template-columns: repeat(2, 1fr); /* 2 colunas */
                gap: 12px;
                margin-bottom: 50px;
            }
            .metric-card {
                background-color: #1a1c24; /* Fundo Cinza Escuro igual ao box de cima */
                border: 1px solid #444;
                border-radius: 8px;
                padding: 15px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transition: transform 0.2s, border-color 0.2s;
            }
            .metric-card:hover {
                border-color: #4b67ff; /* Efeito hover azul */
                transform: translateY(-2px);
            }
            .metric-title {
                font-size: 0.8rem;
                color: #a0a0a0 !important;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 5px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .metric-value {
                font-size: 1.6rem;
                font-weight: 700;
                color: #ffffff !important;
            }
            .metric-sub {
                font-size: 0.75rem;
                color: #888 !important;
                margin-top: 2px;
            }
            /* --- Contexto da Seção 6 --- */
            .section-context-box {
                background-color: rgba(75, 103, 255, 0.1);
                border: 1px solid #4b67ff;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
            /* --- Tabela de Auditoria --- */
            .audit-row { 
                display: flex; 
                justify-content: space-between; 
                border-bottom: 1px solid #333; 
                padding: 8px 0;
                font-family: monospace;
            }
            /* --- Caixa de Texto --- */
            .text-box {
                display: flex;
                text-align: justify;
                background-color: rgba(255,255,255,0.05);
                padding: 10px;
                border-radius: 5px;
                font-size: 0.95em;
                line-height: 1.5;
            }
        </style>
    """, unsafe_allow_html=True)

set_custom_theme()

# --------------------------------------------------------------------------- #
#                      GERENCIAMENTO DE ESTADO & CACHE                        #
# --------------------------------------------------------------------------- #

# Inicializa variáveis de sessão
if 'favorites' not in st.session_state: st.session_state.favorites = {}
if 'blacklist' not in st.session_state: st.session_state.blacklist = {}
if 'search_history' not in st.session_state: st.session_state.search_history = []
if 'current_results' not in st.session_state: st.session_state.current_results = []
if 'refined_query' not in st.session_state: st.session_state.refined_query = ""
if 'view_mode' not in st.session_state: st.session_state.view_mode = "search"
if 'selected_prof' not in st.session_state: st.session_state.selected_prof = None
if 'last_weights' not in st.session_state: st.session_state.last_weights = {}
# Armazena a estrutura hierárquica extraída pelo LLM
if 'student_area_struct' not in st.session_state: st.session_state.student_area_struct = {}
if 'inferred_areas' not in st.session_state: st.session_state.inferred_areas = {} # Cache de inferência

# --- OTIMIZAÇÃO: Caching das Funções Pesadas ---
# O Streamlit não recalculará isso se os parâmetros não mudarem.
# 'ttl=3600' mantém o cache por 1 hora.
@st.cache_data(ttl=3600, show_spinner=False)
def cached_recommendation_engine(query, weights, student_area_struct):
    # Passamos a estrutura de área do aluno para o backend
    return thesis_recommendation_engine(query, False, weights, student_area_struct)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_get_publications(prof_id, limit):
    """ Wrapper com cache para busca de publicações no banco. """
    return get_publications_by_professor_id(prof_id, limit)

# --------------------------------------------------------------------------- #
#                   INTEGRAÇÃO COM LLMS (OLLAMA / GEMINI)                     #
# --------------------------------------------------------------------------- #

def call_ollama(prompt, model="mistral"):
    url = "http://localhost:11434/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}} # Temp baixa para JSON
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Erro ao conectar com Ollama: {e}"

def call_gemini(prompt, api_key, model="gemini-2.5-flash"):
    """ Chamada REST simples para Gemini com Fallback automático """
    if not api_key: return "Chave de API não configurada."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json={"contents": [{"parts": [{"text": prompt}]}]})
        if response.status_code == 200:
            # Parse seguro da resposta Gemini
            try:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                return "Erro: Resposta vazia da API Gemini."
        elif response.status_code == 404 and model == "gemini-2.5-flash":
            # FALLBACK: Se o 2.5 Flash der 404, tenta o modelo estável 'gemini-pro' automaticamente
            return call_gemini(prompt, api_key, model="gemini-pro")
        else:
            return f"Erro na API Gemini ({model}): {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erro de conexão: {e}"

def llm_extract_cnpq_areas(user_text, provider, model_name, api_key=None):
    """
    Extrai a hierarquia CNPq (GA, A, SA, E) do texto do aluno para fidelidade matemática à Tese.
    """
    if provider == "Simulação (sem IA)":
        return {"grande_area": "Ciências Exatas", "area": user_text.split()[0]}
    
    sys_prompt = f"""
    Analise o interesse de pesquisa: '{user_text}'.
    Mapeie para a Tabela de Áreas do Conhecimento do CNPq (Brasil).
    Retorne APENAS um JSON estrito (sem markdown) no formato:
    {{
        "grande_area": "Ex: Ciências Exatas e da Terra",
        "area": "Ex: Ciência da Computação",
        "sub_area": "Ex: Metodologia e Técnicas da Computação",
        "especialidade": "Ex: Engenharia de Software"
    }}
    Se não souber, tente aproximar o máximo possível.
    """
    
    resp = ""
    if provider == "Local (Ollama)": resp = call_ollama(sys_prompt, model_name)
    elif provider == "Nuvem (Gemini)": resp = call_gemini(sys_prompt, api_key)
    
    # Tentativa de parser simples do JSON
    try:
        # Limpa markdown ```json ... ``` se o modelo retornar
        clean_resp = resp.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_resp)
    except:
        return {}

def llm_infer_area_from_pubs(prof_name, pubs_list, provider, model_name, api_key=None):
    """
    Infere as Áreas de Conhecimento a partir das publicações (para resolver dados faltantes).
    """
    if not pubs_list: return "Sem dados de publicação para inferir."
    
    pubs_text = "\n".join(pubs_list[:5]) # Usa as 5 primeiras
    
    sys_prompt = f"""
    Com base nos títulos das publicações abaixo do professor {prof_name}, infira as Áreas de Conhecimento (CNPq).
    Publicações:
    {pubs_text}
    
    Retorne uma lista formatada e separada por vírgulas.
    Exemplo: Ciência da Computação, Engenharia de Software, Machine Learning.
    Seja conciso.
    """
    
    if provider == "Local (Ollama)": return call_ollama(sys_prompt, model_name)
    elif provider == "Nuvem (Gemini)": return call_gemini(sys_prompt, api_key)
    return "Simulação: Área inferida por IA com base em publicações."

def llm_explain_recommendation(prof_name, score, user_query, provider, model_name, api_key=None):
    """ Gera explicação personalizada """
    if provider == "Simulação (sem IA)":
        random.seed(prof_name + user_query) # Determinístico
        return random.choice([
            f"A trajetória de **{prof_name}** tem forte sinergia com '{user_query}' (Score: {score:.2f}).",
            f"Indicadores de produção e orientação destacam **{prof_name}** para este tema.",
            f"Com base nas métricas da tese, **{prof_name}** é uma recomendação sólida ({score:.2f})."
        ])
    
    prompt = f"Explique em 1 frase por que o professor '{prof_name}' é bom para '{user_query}' (Score {score:.1f})."
    if provider == "Local (Ollama)": return call_ollama(prompt, model_name)
    elif provider == "Nuvem (Gemini)": return call_gemini(prompt, api_key)
    return ""

def format_areas_display(raw_areas):
    """
    Limpa a string bruta do banco, remove duplicatas, conserta capitalização 
    e remove underlines. Retorna uma lista limpa.
    """
    if not raw_areas or "Inferido" in raw_areas:
        return "Área não cadastrada formalmente."
    
    # Divide as cadeias de hierarquia
    chains = raw_areas.split(' | ')
    clean_terms = set()
    
    for chain in chains:
        parts = chain.split('#')
        for p in parts:
            p = p.strip()
            if p and p != '-' and p.lower() != 'não informado':
                # Remove underlines e ajusta Capitalização (Title Case)
                cleaned_term = p.replace('_', ' ').title()
                
                # Ajuste fino para preposições em pt-BR (da, de, do, e)
                cleaned_term = re.sub(r'\b(Da|De|Do|E|Em|Para)\b', lambda m: m.group(0).lower(), cleaned_term)
                
                clean_terms.add(cleaned_term)
    
    # Ordena alfabeticamente
    sorted_terms = sorted(list(clean_terms))
    return ", ".join(sorted_terms)

def llm_summarize_profile(prof_name, raw_areas_text, provider, model_name, api_key=None):
    """
    Usa LLM para criar um resumo profissional legível a partir da sopa de palavras-chave.
    """
    if provider == "Simulação (sem IA)":
        return None # Retorna None para usar a lista formatada padrão
        
    prompt = f"""
    Aja como um redator acadêmico. Com base nas seguintes áreas de conhecimento cruas do Currículo Lattes:
    "{raw_areas_text}"
    
    Escreva um resumo de 1 parágrafo (máximo 2 linhas) descrevendo o perfil de pesquisa do professor {prof_name}.
    Comece com "Pesquisador(a) com ênfase em..." ou "Especialista em...".
    Não use markdown, não use listas, apenas texto corrido e fluido em português.
    Corrija formatações estranhas (ex: tire underlines).
    """
    
    if provider == "Local (Ollama)": return call_ollama(prompt, model_name)
    elif provider == "Nuvem (Gemini)": return call_gemini(prompt, api_key)
    return None

def parse_cnpq_hierarchy(raw_areas):
    """
    Extrai a hierarquia CNPq mais relevante da string bruta para exibição estruturada.
    Lida com campos vazios e formata corretamente.
    """
    if not raw_areas or "Inferido" in raw_areas:
        return {}
        
    # Pega a primeira cadeia como principal
    chain = raw_areas.split(' | ')[0]
    parts = chain.split('#')
    
    # Limpa e substitui vazios por '-'
    clean_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            clean_parts.append("-")
        else:
            clean_parts.append(p)
            
    # Garante 4 elementos (GA, A, SA, E)
    clean_parts += ["-"] * (4 - len(clean_parts))
    
    return {
        "Grande Área": clean_parts[0],
        "Área": clean_parts[1],
        "Subárea": clean_parts[2],
        "Especialidade": clean_parts[3]
    }

# --------------------------------------------------------------------------- #
#       LÓGICA DE INTERFACE & NAVEGAÇÃO                                       #
# --------------------------------------------------------------------------- #

def toggle_favorite(prof):
    """ Adiciona ou remove dos favoritos com feedback visual """
    pid = prof['id']
    if pid in st.session_state.favorites:
        del st.session_state.favorites[pid]
        st.toast("Removido.", icon="🗑️")
    else:
        # Se estava na blacklist, remove de lá primeiro
        if pid in st.session_state.blacklist: del st.session_state.blacklist[pid]
        st.session_state.favorites[pid] = prof # Salva o objeto inteiro
        st.toast("Favoritado!", icon="⭐")

def toggle_blacklist(prof):
    """ Adiciona ou remove da lista de ocultos """
    pid = prof['id']
    if pid in st.session_state.blacklist:
        del st.session_state.blacklist[pid]
        st.toast("Restaurado.", icon="👁️")
    else:
        # Se estava nos favoritos, remove de lá primeiro
        if pid in st.session_state.favorites: del st.session_state.favorites[pid]
        st.session_state.blacklist[pid] = prof
        # Remove da lista visual atual imediatamente para feedback instantâneo
        st.session_state.current_results = [p for p in st.session_state.current_results if p['id'] != pid]
        st.toast("Ocultado.", icon="🚫")

# --------------------------------------------------------------------------- #
#       BARRA LATERAL (CONFIGURAÇÕES DO MODELO)                               #
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🎓 RecomendaProf")
    st.markdown("*Implementação do Modelo Matemático (Radi, 2025)*")
    st.divider()
    
    # --- Configuração do Modelo ---
    st.subheader("⚙️ Parâmetros do Modelo")
    help_modes = "Padrão: Pesos equilibrados (Área 0.2, Exp 0.2, Prod 0.2).\nAvançado: Ajuste manual de cada dimensão."
    mode = st.radio("Modo de Operação", ["Padrão (Otimizado)", "Avançado (6 Variáveis)"], help=help_modes)
    
    # Pesos (Dicionário que será passado ao backend)
    weights = {'area': 0.2, 'exp': 0.2, 'prod': 0.2, 'efi': 0.1, 'colab': 0.1, 'pesq': 0.1, 'qual': 0.0}
    
    if mode == "Avançado (6 Variáveis)":
        with st.expander("⚖️ Personalizar Pesos", expanded=True):
            st.markdown("Ajuste a importância de cada critério no cálculo.")
            w_area = st.slider("Área (aderência)", 0.0, 1.0, 0.2, 0.05, help="Peso da compatibilidade temática.")
            w_exp = st.slider("Experiência (orientações)", 0.0, 1.0, 0.2, 0.05, help="Peso do volume histórico de orientações.")
            w_prod = st.slider("Produção (publicações)", 0.0, 1.0, 0.2, 0.05, help="Peso do volume bibliográfico.")
            w_efi = st.slider("Eficiência (conclusão)", 0.0, 1.0, 0.1, 0.05, help="Peso da taxa de sucesso (conclusão/total).")
            w_colab = st.slider("Colaboração (redes)", 0.0, 1.0, 0.1, 0.05, help="Peso da inserção em bancas e redes.")
            w_pesq = st.slider("Pesquisa (projetos)", 0.0, 1.0, 0.1, 0.05, help="Peso da participação em projetos de pesquisa.")
            
            weights = {
                'area': w_area, 'exp': w_exp, 'prod': w_prod, 
                'efi': w_efi, 'colab': w_colab, 'pesq': w_pesq, 'qual': 0.0
            }

            # --- WARNING DE SOMA DOS PESOS ---
            total_w = sum(weights.values())
            # Normaliza para a barra (max 2.0 para visualização)
            bar_val = min(total_w / 2.0, 1.0)
            
            st.markdown(f"**Soma dos Pesos: {total_w:.1f}**")
            
            if 0.9 <= total_w <= 1.1:
                st.progress(bar_val, text="Equilibrado (Ideal)")
            elif total_w < 0.9:
                st.progress(bar_val)
                st.warning("⚠️ Soma baixa (< 1.0). Os scores finais serão reduzidos.")
            else:
                st.progress(bar_val)
                st.warning("⚠️ Soma alta (> 1.0). Os scores podem ficar inflacionados.")

    st.divider()
    
    # --- Configuração de IA ---
    with st.expander("🧠 Configuração de IA"):
        llm_provider = st.selectbox("Provedor", ["Simulação (sem IA)", "Local (Ollama)", "Nuvem (Gemini)"])
        ollama_model, api_key = "mistral", None
        if llm_provider == "Local (Ollama)":
            ollama_model = st.text_input("Modelo", "mistral", help="Nome do modelo no Ollama (ex: llama3, mistral)")
            st.caption("Certifique-se de que o 'ollama serve' está rodando.")

        elif llm_provider == "Nuvem (Gemini)":
            api_key = st.text_input("Gemini API Key", type="password",  help="Obtenha grátis em aistudio.google.com")


    # --- Gerenciamento de Listas (Favoritos / Ocultos) ---
    
    # Favoritos
    if st.session_state.favorites:
        st.divider()
        st.subheader(f"⭐ Favoritos ({len(st.session_state.favorites)})")
        for fid, fdat in st.session_state.favorites.items():
            if st.button(f"{fdat['nome'][:20]}...", key=f"side_fav_{fid}", use_container_width=True, help="Clique para ver detalhes"):
                st.session_state.selected_prof = fdat
                st.session_state.view_mode = "single_view"
                st.rerun()
    
    # Ocultados (Blacklist)
    if st.session_state.blacklist:
        st.divider()
        with st.expander(f"🚫 Ocultados ({len(st.session_state.blacklist)})"):
             for pid, pdata in list(st.session_state.blacklist.items()):
                c1, c2 = st.columns([3, 1], vertical_alignment="center")
                c1.markdown(f"- {pdata['nome'][:20]}")
                if c2.button("↺", key=f"rest_{pid}", help="Restaurar para a lista"):
                    del st.session_state.blacklist[pid]
                    st.rerun()

# --------------------------------------------------------------------------- #
#       ÁREA PRINCIPAL                                                        #
# --------------------------------------------------------------------------- #

# --- VIEW 1: DETALHES DO PROFESSOR ---
if st.session_state.view_mode == "single_view" and st.session_state.selected_prof:
    p = st.session_state.selected_prof
    det = p.get('details', {})
    info = p.get('info', {})

    if st.button("← Voltar à Busca"):
        st.session_state.view_mode = "search"
        st.session_state.selected_prof = None
        st.rerun()

    st.title(p['nome'])

    # Formatação de Áreas e Idiomas
    # Limpando os dados brutos primeiro
    raw_areas_db = info.get('raw_hierarchy', '')
    clean_list_text = format_areas_display(raw_areas_db)
    
    # Tentando gerar resumo com IA (se o provedor não for Simulação) usando session_state para não re-gerar a cada clique
    cache_key = f"summary_{p['id']}"
    if cache_key not in st.session_state:
        with st.spinner("Gerando resumo do perfil acadêmico..."):
            summary = llm_summarize_profile(p['nome'], clean_list_text, llm_provider, ollama_model, api_key)
            st.session_state[cache_key] = summary

    # Decide o que mostrar: O resumo da IA ou a lista limpa
    display_text = st.session_state[cache_key] if st.session_state[cache_key] else clean_list_text
    
    idiomas_display = info.get('idiomas', 'Não informado')

    st.markdown("### 🎓 Perfil do Pesquisador")
    with st.container(border=True):
        st.markdown(f"""
        <div class="academic-info-box">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div style="display: flex; flex-direction: column; gap: 10px; border-right: 1px solid #333; padding-right: 10px;">
                    <div>
                        <span class="info-label">🏛️ Instituição:</span>
                        <div class="text-box">
                            {info.get('universidade', 'N/A')} ({info.get('sigla', '')})
                        </div>
                    </div>
                    <div>
                        <span class="info-label">🎓 Titulação:</span>
                        <div class="text-box">
                            {info.get('titulacao', 'N/A')} ({info.get('ano_doutorado', '?')})
                        </div>
                    </div>
                    <div>
                        <span class="info-label">🗣️ Idiomas:</span>
                            <div class="text-box">
                                {idiomas_display}
                            </div>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column;">
                    <span class="info-label">🧠 Áreas de Atuação:</span>
                    <div class="text-box " style="flex-grow: 1; min-height: 80px;">
                        {display_text}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        lattes_url = f"https://www.google.com/search?q=Currículo+Lattes+{p['nome'].replace(' ', '+')}"
        st.link_button("🌐 Acessar Currículo Lattes (Verificado)", lattes_url, type="primary", use_container_width=True)

    # Métricas
    st.markdown(f"### Score Geral: <span style='color:#4b67ff'>{p['hybrid_score']:.2f}</span>", unsafe_allow_html=True)
    visual_score_norm = min(p['hybrid_score'] / 1.0, 1.0) # Normalizado para 1.0
    st.progress(visual_score_norm)
    
    st.divider()
    st.subheader("📊 Análise Multidimensional")
    
    # Prepara os valores calculados
    w_calc = st.session_state.last_weights if st.session_state.last_weights else weights
    
    # Dicionário auxiliar para ícones e cálculos
    # Formato: (Label, Ícone, Valor Bruto Normalizado, Peso, Descrição Curta)
    metrics_data = [
        ("Área", "🎯", det.get('raw_area', 0), w_calc.get('area', 0.2), "Aderência Temática"),
        ("Experiência", "🎓", det.get('raw_exp', 0), w_calc.get('exp', 0.2), "Orientações"),
        ("Produção", "📚", det.get('raw_prod', 0), w_calc.get('prod', 0.2), "Volume Bibliográfico"),
        ("Eficiência", "⚡", det.get('raw_efi', 0), w_calc.get('efi', 0.1), "Taxa Conclusão"),
        ("Colaboração", "🤝", det.get('raw_colab', 0), w_calc.get('colab', 0.1), "Redes/Bancas"),
        ("Pesquisa", "🔬", det.get('raw_pesq', 0), w_calc.get('pesq', 0.1), "Projetos/Qualis")
    ]

    # Container Principal
    with st.container():
        col_metrics, col_chart = st.columns([1.2, 1], gap="medium", vertical_alignment="center")
        
        # --- COLUNA DA ESQUERDA: GRID DE CARDS ---
        with col_metrics:
            html_cards = '<div class="metric-container">'
            for label, icon, raw_val, weight, desc in metrics_data:
                final_val = raw_val * weight
                html_cards += f"""<div class="metric-card">
                    <div class="metric-title">{icon} {label}</div>
                    <div class="metric-value">{final_val:.2f}</div>
                    <div class="metric-sub">{desc}</div>
                </div>
                """
            html_cards += '</div>'
            st.markdown(html_cards, unsafe_allow_html=True)

        # --- COLUNA DA DIREITA: GRÁFICO DE RADAR ---
        with col_chart:
            # Dados para o Radar Chart
            categories = [m[0] for m in metrics_data]
            values = [m[2] for m in metrics_data] # Usa valor bruto (0-1) para o radar preencher corretamente
            
            # Fecha o ciclo
            values += values[:1]
            categories += categories[:1]

            fig = go.Figure(data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=p['nome'],
                line_color='#4b67ff',
                fillcolor='rgba(75, 103, 255, 0.2)', # Azul translúcido
                marker=dict(color='#4b67ff', size=4),
            ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1], gridcolor='#333', tickfont=dict(size=8, color='#666')),
                    bgcolor='rgba(0,0,0,0)',
                    angularaxis=dict(gridcolor='#333', linecolor='#4b67ff', tickfont=dict(size=11, color='#ddd'))
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=30, r=30, t=30, b=30),
                showlegend=False,
                height=600
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Auditoria Detalhada
    with st.expander("🧮 Auditoria do Cálculo (Validar Pesos)", expanded=True):
        st.markdown("Confira como o **Score Final** foi calculado multiplicando a nota normalizada de cada dimensão pelo peso escolhido.")
        
        def audit_line(label, raw_val, weight_key):
            w_val = w_calc.get(weight_key, 0.0)
            contrib = raw_val * w_val
            st.markdown(
                f"<div class='audit-row'>"
                f"<span>{label}</span>"
                f"<span>{raw_val:.3f} (Nota) x {w_val:.2f} (Peso) = <strong>{contrib:.3f}</strong></span>"
                f"</div>", 
                unsafe_allow_html=True
            )

        audit_line("🎯 Área", det.get('raw_area', 0), 'area')
        audit_line("🎓 Experiência", det.get('raw_exp', 0), 'exp')
        audit_line("📚 Produção", det.get('raw_prod', 0), 'prod')
        audit_line("⚡ Eficiência", det.get('raw_efi', 0), 'efi')
        audit_line("🤝 Colaboração", det.get('raw_colab', 0), 'colab')
        audit_line("🔬 Pesquisa", det.get('raw_pesq', 0), 'pesq')
        
        st.divider()
        st.caption("Nota: As 'Notas' acima são valores normalizados entre 0 e 1, relativos ao máximo do dataset.")

    # Auditoria de Dados Brutos
    with st.expander("📂 Auditoria de Dados Brutos (Absolutos)"):
        st.markdown("Estes são os valores reais extraídos do banco de dados antes da normalização.")
        c_a, c_b = st.columns(2)
        c_a.metric("Total de Orientações", f"{det.get('abs_exp', 'N/A')}")
        c_b.metric("Pontos Totais de Prod.", f"{det.get('abs_prod', 'N/A')}")
        st.caption("Usado para calcular Experiência e Produção.")
        
    st.divider()
    st.subheader("Publicações Recentes")
    pubs, total = cached_get_publications(p['id'], 10)
    if pubs:
        for pub in pubs: st.markdown(f"- {pub}")
        if total > 10: st.caption(f"E mais {total - 10} publicações no banco.")
    else:
        st.warning("Sem publicações registradas no período recente.")

# --- VIEW 2: BUSCA E RESULTADOS ---
else:
    st.title("Encontre seu Orientador Ideal")
    
    # Contexto Acadêmico
    st.markdown("""
    <div class="section-context-box">
        <strong>Contexto Experimental:</strong><br>
        Esta ferramenta materializa a implementação computacional do <strong>modelo matemático da Tese de Doutorado de <em>Radi Melo Martins (2025)</em> [1]</strong>.
        Utilize a busca abaixo para validar a sensibilidade das 6 dimensões propostas (Área, Experiência, Eficiência, Produção, Colaboração, Pesquisa).
    </div>
    """, unsafe_allow_html=True)

    # --- HISTÓRICO DE CHAT ---
    if st.session_state.search_history:
        with st.expander("Ver histórico da conversa", expanded=False):
            for msg in st.session_state.search_history:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Input de Busca
    prompt = st.chat_input("Ex: Sou um estudante de Ciência da Computação e para a minha pós, gostaria de um(a) orientador(a) com expertise em...")
    
    if prompt:
        st.session_state.search_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.status("🔍 Processando...", expanded=True) as status:
            st.write("Extraindo estrutura hierárquica (CNPq) com IA...")
            # Extração da estrutura hierárquica para o cálculo de P_Area fiel
            area_struct = llm_extract_cnpq_areas(prompt, llm_provider, ollama_model, api_key)
            st.session_state.student_area_struct = area_struct
            
            # Mostra o que a IA entendeu (Debug útil para validação)
            st.toast(f"Mapeado para: {area_struct.get('area', 'N/A')} > {area_struct.get('sub_area', 'N/A')}", icon="🤖")
            
            st.write("Calculando scores multidimensionais...")
            st.session_state.last_weights = weights.copy()
            
            try:
                # Passa a estrutura para o motor
                results = cached_recommendation_engine(prompt, weights, area_struct)

                # Filtra blacklist
                valid_results = [r for r in results if r['id'] not in st.session_state.blacklist]
                st.session_state.current_results = valid_results
                status.update(label="Busca Completa!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Erro no cálculo: {e}")
                st.session_state.current_results = []

    # Renderização de Resultados
    if st.session_state.current_results:
        st.divider()
        st.subheader(f"Resultados para: \n{st.session_state.refined_query}")

        # Encontra o maior score ATUAL para normalizar a barra de progresso (evita barra cheia sempre)        
        max_score = max([p['hybrid_score'] for p in st.session_state.current_results]) if st.session_state.current_results else 1.0

        for prof in st.session_state.current_results[:5]: # Top 5 resultados
            is_fav = prof['id'] in st.session_state.favorites
            
            # Card Container
            with st.container(border=True):
                col_info, col_actions = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"### {prof['nome']}")
                    
                    # Barra de Score Relativa ao Máximo da Busca Atual
                    rel_score = prof['hybrid_score'] / max_score if max_score > 0 else 0
                    st.progress(rel_score)
                    
                    det = prof.get('details', {})
                    resumo = (f"Area:{det.get('raw_area',0):.2f} | Exp:{det.get('raw_exp',0):.2f} | Prod:{det.get('raw_prod',0):.2f} | "
                              f"Efi:{det.get('raw_efi',0):.2f}")
                    st.markdown(f"<div class='score-container'> <span class='metric-label'>📊 Métricas: {resumo}</span> --> <strong>Pontuação: {prof['hybrid_score']:.2f}</strong></div> ", unsafe_allow_html=True)

                with col_actions:
                    # Botões Verticais
                    if st.button("★ Nos favoritos" if is_fav else "☆ Adicionar aos favoritos", key=f"fav_{prof['id']}", type="primary" if is_fav else "secondary", use_container_width=True, help="Adiciona esse(a) professor(a) à lista de favoritos"):
                        toggle_favorite(prof)
                        st.rerun()
                    
                    if st.button("📄 Ver mais detalhes", key=f"view_{prof['id']}", use_container_width=True, help="Carrega página com mais informações das variáveis e publicações"):
                        st.session_state.selected_prof = prof
                        st.session_state.view_mode = "single_view"
                        st.rerun()
                    
                    if st.button("🚫 Ocultar professor", key=f"hide_{prof['id']}", use_container_width=True, help="Adiciona esse(a) professor(a) à lista de ocultos"):
                        toggle_blacklist(prof)
                        st.rerun()

    elif not st.session_state.current_results and st.session_state.refined_query:
        st.info("Nenhum resultado encontrado para os critérios atuais.")
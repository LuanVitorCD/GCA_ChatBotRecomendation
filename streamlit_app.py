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
            .metric-label { font-size: 0.75rem; color: #bbb; text-transform: uppercase; letter-spacing: 0.5px; }
            .metric-value { font-size: 1.1rem; color: #fff; font-weight: bold; }
            
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
                padding: 4px 0;
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
# Armazena os pesos usados na última busca para a auditoria
if 'last_weights' not in st.session_state: st.session_state.last_weights = {}

# --- OTIMIZAÇÃO: Caching das Funções Pesadas ---
# O Streamlit não recalculará isso se os parâmetros não mudarem.
# 'ttl=3600' mantém o cache por 1 hora.
@st.cache_data(ttl=3600, show_spinner=False)
def cached_recommendation_engine(query, weights):
    # O cache precisa que 'weights' seja hashable. Dicionários normais funcionam no streamlit novo.
    return thesis_recommendation_engine(query, False, weights)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_get_publications(prof_id, limit):
    """ Wrapper com cache para busca de publicações no banco. """
    return get_publications_by_professor_id(prof_id, limit)

# --------------------------------------------------------------------------- #
#                   INTEGRAÇÃO COM LLMS (OLLAMA / GEMINI)                     #
# --------------------------------------------------------------------------- #

def call_ollama(prompt, model="mistral"):
    url = "http://localhost:11434/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.7}}
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

def llm_refine_query(user_text, provider, model_name, api_key=None):
    """ Refina a busca do usuário para termos técnicos """
    if provider == "Simulação (sem IA)":
        return user_text if len(user_text.split()) > 2 else user_text + " pesquisa tecnologia"
    
    sys_prompt = f"Converta para palavras-chave acadêmicas (Lattes): '{user_text}'. Retorne apenas as palavras separadas por vírgula."
    
    if provider == "Local (Ollama)": return call_ollama(sys_prompt, model_name)
    elif provider == "Nuvem (Gemini)": return call_gemini(sys_prompt, api_key)
    return user_text

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
    help_modes = """
    Padrão (Otimizado): Usa pesos fixos equilibrados (Área: 0.2, Exp: 0.2, Prod: 0.2, Outros: 0.1).\n
    Avançado (6 Variáveis): Permite ajustar manualmente a importância de cada critério.
    """
    mode = st.radio("Modo de Operação", ["Padrão (Otimizado)", "Avançado (6 Variáveis)"], help=help_modes)
    
    # Pesos (Dicionário que será passado ao backend)
    weights = {'area': 0.2, 'exp': 0.2, 'prod': 0.2, 'efi': 0.1, 'colab': 0.1, 'pesq': 0.1, 'qual': 0.0}
    
    if mode == "Avançado (6 Variáveis)":
        with st.expander("⚖️ Personalizar Pesos", expanded=True):
            w_area = st.slider("Área", 0.0, 1.0, 0.2, 0.1)
            w_exp = st.slider("Experiência", 0.0, 1.0, 0.2, 0.1)
            w_prod = st.slider("Produção", 0.0, 1.0, 0.2, 0.1)
            w_efi = st.slider("Eficiência", 0.0, 1.0, 0.1, 0.1)
            w_colab = st.slider("Colaboração", 0.0, 1.0, 0.1, 0.1)
            w_pesq = st.slider("Pesquisa", 0.0, 1.0, 0.1, 0.1)
            
            weights = {
                'area': w_area, 'exp': w_exp, 'prod': w_prod, 
                'efi': w_efi, 'colab': w_colab, 'pesq': w_pesq, 'qual': 0.0
            }

            # --- WARNING DE SOMA DOS PESOS ---
            total_w = sum(weights.values())
            # Normaliza para a barra (max 2.0 para visualização)
            bar_val = min(total_w / 2.0, 1.0)
            
            st.markdown("---")
            st.write(f"**Soma dos Pesos: {total_w:.1f}**")
            
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
            ollama_model = st.text_input("Modelo", "mistral", help="Ex: llama3, mistral")
            st.caption("Certifique-se de que o 'ollama serve' está rodando.")

        elif llm_provider == "Nuvem (Gemini)":
            api_key = st.text_input("Gemini API Key", type="password",  help="Obtenha grátis em aistudio.google.com")


    # --- Gerenciamento de Listas (Favoritos / Ocultos) ---
    
    # Favoritos
    if st.session_state.favorites:
        st.divider()
        st.subheader(f"⭐ Favoritos ({len(st.session_state.favorites)})")
        for fid, fdat in st.session_state.favorites.items():
            if st.button(f"{fdat['nome'][:22]}...", key=f"side_fav_{fid}"):
                st.session_state.selected_prof = fdat
                st.session_state.view_mode = "single_view"
                st.rerun()
    
    # Ocultados (Blacklist)
    if st.session_state.blacklist:
        st.divider()
        with st.expander(f"🚫 Ocultados ({len(st.session_state.blacklist)})"):
             for pid, pdata in list(st.session_state.blacklist.items()):
                c1, c2 = st.columns([3, 1])
                c1.caption(pdata['nome'][:20])
                if c2.button("↺", key=f"rest_{pid}", help="Restaurar"):
                    del st.session_state.blacklist[pid]
                    st.rerun()

# --------------------------------------------------------------------------- #
#       ÁREA PRINCIPAL                                                        #
# --------------------------------------------------------------------------- #

# --- VIEW 1: DETALHES DO PROFESSOR ---
if st.session_state.view_mode == "single_view" and st.session_state.selected_prof:
    p = st.session_state.selected_prof
    det = p.get('details', {})
    
    if st.button("← Voltar à Busca"):
        st.session_state.view_mode = "search"
        st.session_state.selected_prof = None
        st.rerun()

    st.title(p['nome'])
    # Cálculo relativo da barra de progresso (para visualização apenas)
    # Se o score passar de 10, normaliza visualmente até 20, ou usa o próprio valor se for baixo
    visual_score_norm = min(p['hybrid_score'] / 10.0, 1.0) if p['hybrid_score'] > 1.0 else p['hybrid_score']
    
    st.markdown(f"### Score Geral: <span style='color:#4b67ff'>{p['hybrid_score']:.2f}</span>", unsafe_allow_html=True)
    st.progress(visual_score_norm)
    
    # --- AUDITORIA DE CÁLCULO (Inserida abaixo das métricas grandes) ---
    # Primeiro os stats grandes mantidos
    
    # Explicação IA (Mantida)
    query = st.session_state.refined_query or "pesquisa acadêmica"
    expl = llm_explain_recommendation(p['nome'], p['hybrid_score'], query, llm_provider, ollama_model, api_key)
    if expl: st.info(f"💡 **Análise IA:** {expl}")

    # Métricas Detalhadas (Grid com todas as variáveis)
    st.subheader("📊 Resultado das Variáveis")
    w_calc = st.session_state.last_weights if st.session_state.last_weights else weights
    
    # Linha 1: Variáveis principais de impacto
    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 Área", f"{(1.0 * w_calc.get('area', 0.2)):.2f}")
    c2.metric("🎓 Experiência", f"{(det.get('raw_exp', 0) * w_calc.get('exp', 0.2)):.2f}")
    c3.metric("📚 Produção", f"{(det.get('raw_prod', 0) * w_calc.get('prod', 0.2)):.2f}")
    
    
    # Linha 2: Variáveis secundárias e contexto
    c4, c5, c6 = st.columns(3)
    c4.metric("⚡ Eficiência", f"{(det.get('raw_efi', 0) * w_calc.get('efi', 0.1)):.2f}")
    c5.metric("🤝 Colaboração", f"{(det.get('raw_colab', 0) * w_calc.get('colab', 0.1)):.2f}")

    val_pesq = det.get('raw_pesq', det.get('raw_prod', 0) * 0.5)
    c6.metric("🔬 Pesquisa", f"{(val_pesq * w_calc.get('pesq', 0.1)):.2f}")

    # Auditoria (Expanders)
    with st.expander("🧮 Auditoria do Cálculo (Validar Pesos)", expanded=True):
        st.markdown("Confira como o **Score Final** foi calculado multiplicando a nota de cada dimensão pelo peso escolhido.")
        
        # Recupera pesos usados (ou padrão se não tiver)
        w_used = st.session_state.last_weights if st.session_state.last_weights else weights
        
        # Helper para linha da tabela
        def audit_line(label, raw_val, weight_key):
            w_val = w_used.get(weight_key, 0.0) # 0.0 se não existir
            contrib = raw_val * w_val
            st.markdown(
                f"<div class='audit-row'>"
                f"<span>{label}</span>"
                f"<span>{raw_val:.2f} (Nota) x {w_val:.2f} (Peso) = <strong>{contrib:.2f}</strong></span>"
                f"</div>", 
                unsafe_allow_html=True
            )
            return contrib

        audit_line("🎯 Área", 1.0, 'area')
        audit_line("🎓 Experiência", det.get('raw_exp', 0), 'exp')
        audit_line("📚 Produção", det.get('raw_prod', 0), 'prod')
        audit_line("⚡ Eficiência", det.get('raw_efi', 0), 'efi')
        audit_line("🤝 Colaboração", det.get('raw_colab', 0), 'colab')
        # Pesquisa (derivado se não existir)
        val_pesq = det.get('raw_pesq', det.get('raw_prod', 0) * 0.5)
        audit_line("🔬 Pesquisa", val_pesq, 'pesq')
        
        st.divider()
        st.caption("Nota: As 'Notas' acima são normalizadas (ex: pontos por ano). Para ver contagens totais absolutas, veja a auditoria de dados brutos abaixo.")

    # Auditoria de Dados Brutos (sem Qualis)
    with st.expander("📂 Auditoria de Dados Brutos (Absolutos)"):
        c_a, c_b = st.columns(2)
        c_a.metric("Total de Orientações", f"{det.get('abs_exp', 'N/A')}")
        c_b.metric("Pontos Totais de Prod.", f"{det.get('abs_prod', 'N/A')}")

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
    
    # Contexto Acadêmico (Visualização Otimizada)
    st.markdown("""
    <div class="section-context-box">
        <strong>🧪 Contexto Experimental (Seção 6):</strong><br>
        Esta ferramenta materializa a implementação computacional do <strong>modelo matemático da Tese de Doutorado de <em>Radi Melo Martins (2025)</em> [1]</strong>.
        Utilize a busca abaixo para validar a sensibilidade das 6 dimensões propostas (Área, Experiência, Eficiência, Produção, Colaboração, Pesquisa).
    </div>
    """, unsafe_allow_html=True)

    # --- HISTÓRICO DE CHAT ---
    if st.session_state.search_history:
        with st.expander("Ver histórico da conversa", expanded=False):
            for msg in st.session_state.search_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    # Input de Busca
    prompt = st.chat_input("Ex: Sou um estudante de Ciência da Computação e para a minha pós, gostaria de um(a) orientador(a) com expertise em...")
    
    if prompt:
        st.session_state.search_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.status("🔍 Processando...", expanded=True) as status:
            # 1. Refinamento
            st.write("Refinando consulta...")
            refined = llm_refine_query(prompt, llm_provider, ollama_model, api_key)
            st.session_state.refined_query = refined
            
            # 2. Busca (Com Cache)
            # Salva os pesos usados nesta busca para a auditoria bater certo
            st.session_state.last_weights = weights.copy()
            
            st.write("Calculando scores multidimensionais...")
            try:
                results = cached_recommendation_engine(refined, weights)
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
                    
                    # Mini-resumo COMPLETO das 6 variáveis
                    det = prof.get('details', {})
                    # Usamos nomes curtos para caber
                    pesq_val = det.get('raw_pesq', det.get('raw_prod',0)*0.5)
                    # Exibe os valores NORMALIZADOS (Notas)
                    resumo = (f"Area:1.0 | Exp:{det.get('raw_exp',0):.1f} | Prod:{det.get('raw_prod',0):.1f} | "
                              f"Efi:{det.get('raw_efi',0):.1f} | Colab:{det.get('raw_colab',0):.1f} | Pesq:{pesq_val:.1f}")
                    st.markdown(f"<div class='score-container'> <span class='metric-label'>📊 Métricas: {resumo}</span> --> <strong>Pontuação: {prof['hybrid_score']:.2f}</strong></div> ", unsafe_allow_html=True)

                with col_actions:
                    # Botões Verticais
                    if st.button("★" if is_fav else "☆", key=f"fav_{prof['id']}", type="primary" if is_fav else "secondary", use_container_width=True, help="Favoritar"):
                        toggle_favorite(prof)
                        st.rerun()
                    
                    if st.button("📄 Ver", key=f"view_{prof['id']}", use_container_width=True):
                        st.session_state.selected_prof = prof
                        st.session_state.view_mode = "single_view"
                        st.rerun()
                    
                    if st.button("🚫", key=f"hide_{prof['id']}", use_container_width=True, help="Ocultar"):
                        toggle_blacklist(prof)
                        st.rerun()

    elif not st.session_state.current_results and st.session_state.refined_query:
        st.info("Nenhum resultado encontrado para os critérios atuais.")
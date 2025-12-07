# streamlit_app.py - Interface Final (SQLite + Pesos Customizáveis + LLM + Favoritos)
import streamlit as st
import requests
import json
import random
import traceback

# --- Importando lógica atualizada (Tese) ---
from utils.thesis_recommend import thesis_recommendation_engine
from utils.db_utils import get_publications_by_professor_id

st.set_page_config(page_title="RecomendaProf - Tese", layout="wide", initial_sidebar_state="expanded")

def set_custom_theme():
    # CSS aprimorado para layout responsivo e moderno
    st.markdown("""
        <style>
            /* Cores Gerais */
            .stApp, .stMarkdown, label, p, span { color: #E0E0E0 !important; }
            h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
            
            /* Botões Primários */
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

            /* Estilo do Breakdown do Score */
            .score-breakdown { 
                font-size: 0.75rem; 
                color: #aaa; 
                background: #252535; 
                padding: 8px; 
                border-radius: 6px; 
                margin-bottom: 12px;
                border-left: 3px solid #4b67ff;
            }
            .score-val { color: #4b67ff; font-weight: bold; }

            /* Alinhamento de Botões na Coluna Direita */
            div[data-testid="column"] button {
                width: 100%;
                margin-bottom: 5px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            /* Ajustes visuais gerais */
            hr { margin: 1.5em 0; border-color: #333; }
        </style>
    """, unsafe_allow_html=True)

set_custom_theme()

# --------------------------------------------------------------------------- #
#                      GERENCIAMENTO DE ESTADO (SESSION STATE)                #
# --------------------------------------------------------------------------- #
# Inicializa todas as variáveis de estado necessárias
if 'favorites' not in st.session_state:
    st.session_state.favorites = {} # Dict {id: {dados}} para acesso rápido e persistência
if 'blacklist' not in st.session_state:
    st.session_state.blacklist = {} # Dict {id: {dados}}
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = []
if 'refined_query' not in st.session_state:
    st.session_state.refined_query = ""
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "search" # Controla navegação: "search" ou "single_view"
if 'selected_prof' not in st.session_state:
    st.session_state.selected_prof = None

# --------------------------------------------------------------------------- #
#                   INTEGRAÇÃO COM LLMS (OLLAMA / GEMINI)                     #
# --------------------------------------------------------------------------- #

def call_ollama(prompt, model="mistral"):
    """ Chama a API local do Ollama """
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

def call_gemini(prompt, api_key, model="gemini-2.5-flash"):
    """ Chamada REST simples para Gemini com Fallback automático """
    if not api_key: return "Chave de API não configurada."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
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
    system_prompt = (
        f"Atue como um assistente acadêmico especialista. "
        f"O usuário vai descrever um tema de pesquisa de forma leiga. "
        f"Sua tarefa é converter isso para 3 a 5 palavras-chave técnicas e acadêmicas "
        f"que seriam encontradas em um Currículo Lattes (Português). "
        f"Retorne APENAS as palavras-chave separadas por espaço, sem introdução.\n\n"
        f"Texto do usuário: '{user_text}'"
    )
    
    if provider == "Simulação":
        # Simulação melhorada que adiciona termos genéricos se for curto o prompt passado
        if len(user_text.split()) < 3: return user_text + " pesquisa desenvolvimento tecnologia"
        return user_text
    elif provider == "Local (Ollama)":
        return call_ollama(system_prompt, model=model_name)
    elif provider == "Nuvem (Gemini)":
        return call_gemini(system_prompt, api_key)
    return user_text

def llm_explain_recommendation(prof_name, score, user_query, provider, model_name, api_key=None):
    """ Gera explicação personalizada do ranking """
    prompt = (
        f"Escreva uma justificativa curta (máximo 2 frases) explicando por que o professor '{prof_name}' "
        f"é uma boa recomendação para um aluno interessado em '{user_query}'. "
        f"O algoritmo deu um score de afinidade de {score:.1f}. Seja profissional, acadêmico e varie o texto."
    )
    
    if provider == "Simulação":
        # Simulação dinâmica de texto baseada em templates
        templates = [
            f"Com base na busca por '{user_query}', o algoritmo identificou **{prof_name}** como forte correspondência (Score: {score:.2f}).",
            f"A trajetória acadêmica de **{prof_name}** apresenta alta sinergia com o tema '{user_query}', refletida no índice {score:.2f}.",
            f"Para o tema '{user_query}', **{prof_name}** destaca-se pela produtividade e experiência na área (Índice: {score:.2f}).",
            f"O perfil de **{prof_name}** alinha-se estrategicamente com '{user_query}', apresentando indicadores sólidos de produção."
        ]
        # Usa o hash do nome para escolher sempre a mesma frase para o mesmo prof (consistência), mas variando entre profs
        random.seed(prof_name + user_query)
        return random.choice(templates)
        
    elif provider == "Local (Ollama)":
        return call_ollama(prompt, model=model_name)
    elif provider == "Nuvem (Gemini)":
        return call_gemini(prompt, api_key)
    return "Explicação indisponível."

# --------------------------------------------------------------------------- #
#       LÓGICA AUXILIAR DE INTERFACE                                          #
# --------------------------------------------------------------------------- #

def toggle_favorite(prof):
    """ Adiciona ou remove dos favoritos com feedback visual """
    prof_id = prof['id']
    if prof_id in st.session_state.favorites:
        del st.session_state.favorites[prof_id]
        st.toast(f"Removido dos favoritos.", icon="🗑️")
    else:
        # Se estava na blacklist, remove de lá primeiro
        if prof_id in st.session_state.blacklist:
            del st.session_state.blacklist[prof_id]
        
        st.session_state.favorites[prof_id] = prof # Salva o objeto inteiro
        st.toast(f"Favoritado!", icon="⭐")

def toggle_blacklist(prof):
    """ Adiciona ou remove da lista de ocultos """
    prof_id = prof['id']
    if prof_id in st.session_state.blacklist:
        del st.session_state.blacklist[prof_id]
        st.toast(f"Restaurado.", icon="👁️")
    else:
        # Se estava nos favoritos, remove de lá primeiro
        if prof_id in st.session_state.favorites:
            del st.session_state.favorites[prof_id]
            
        st.session_state.blacklist[prof_id] = prof
        st.toast(f"Ocultado.", icon="🚫")
        # Remove da lista visual atual imediatamente para feedback instantâneo
        st.session_state.current_results = [p for p in st.session_state.current_results if p['id'] != prof_id]

def clear_search():
    """ Limpa o estado da busca atual """
    st.session_state.current_results = []
    st.session_state.refined_query = ""
    st.session_state.view_mode = "search"
    st.rerun()

def view_professor_details(prof):
    """ Muda para a view de detalhes do professor """
    st.session_state.selected_prof = prof
    st.session_state.view_mode = "single_view"
    st.rerun()

def back_to_search():
    """ Volta para a lista de resultados """
    st.session_state.view_mode = "search"
    st.session_state.selected_prof = None
    st.rerun()

# --------------------------------------------------------------------------- #
#       INTERFACE LATERAL (SIDEBAR)                                           #
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("🎓 RecomendaProf")
    st.caption("Sistema Baseado em Tese (SQLite)")
    
    # --- MODO DE OPERAÇÃO ---
    help_modes = """
    Padrão (Otimizado): Usa pesos fixos equilibrados (Área: 0.2, Exp: 0.2, Prod: 0.2, Outros: 0.1).\n
    Avançado (6 Variáveis): Permite ajustar manualmente a importância de cada critério.
    """
    mode = st.radio("Modo de Cálculo", ["Padrão (Otimizado)", "Avançado (6 Variáveis)"], help=help_modes)
    
    # --- PESOS CUSTOMIZÁVEIS ---
    with st.expander("⚖️ Personalizar Pesos", expanded=(mode == "Avançado (6 Variáveis)")):
        st.markdown("Ajuste a importância de cada critério no cálculo do Índice de Recomendação.")
        
        # Sliders para as 6 variáveis da tese
        w_area = st.slider("Área (Aderência)", 0.0, 1.0, 0.2, 0.1, help="Peso da compatibilidade temática.")
        w_exp = st.slider("Experiência (Orientações)", 0.0, 1.0, 0.2, 0.1, help="Peso do volume de orientações.")
        w_prod = st.slider("Produção (Publicações)", 0.0, 1.0, 0.2, 0.1, help="Peso do volume de artigos e livros.")
        w_efi = st.slider("Eficiência (Conclusão)", 0.0, 1.0, 0.1, 0.1, help="Peso da taxa de sucesso nas orientações.")
        w_colab = st.slider("Colaboração (Redes)", 0.0, 1.0, 0.1, 0.1, help="Peso da coautoria e bancas.")
        w_pesq = st.slider("Pesquisa (Projetos)", 0.0, 1.0, 0.1, 0.1, help="Peso da participação em projetos.")
        
        # Variável extra de qualidade (Qualis) - Ativa por padrão no modo otimizado
        default_qual = 0.1 if mode == "Padrão (Otimizado)" else 0.0
        w_qual = st.slider("Qualis (Qualidade Extra)", 0.0, 1.0, default_qual, 0.1, help="Peso específico para qualidade A1/A2.")

        # Normalização visual da soma dos pesos
        total_w = w_area + w_exp + w_prod + w_efi + w_colab + w_pesq + w_qual
        if total_w == 0: total_w = 1 # Evita divisão por zero
        st.progress(min(total_w / 7, 1.0)) # Visual apenas (indo até 7 para levar em consideração o valor máximo de todas as variáveis)
        if abs(total_w - 1.0) > 0.01:
            st.caption(f"Soma atual: {total_w:.1f} (Ideal: 1.0)")

    # Dicionário de pesos para passar ao backend
    weights = {
        'area': w_area, 'exp': w_exp, 'prod': w_prod, 
        'efi': w_efi, 'colab': w_colab, 'pesq': w_pesq, 'qual': w_qual
    }

    st.divider()
    
    # --- CONFIGURAÇÃO DE IA ---
    st.subheader("🧠 IA Auxiliar")
    llm_provider = st.selectbox("Provedor:", ["Simulação", "Local (Ollama)", "Nuvem (Gemini)"])
    
    ollama_model = "mistral"
    api_key = None
    
    if llm_provider == "Local (Ollama)":
        ollama_model = st.text_input("Modelo Ollama:", value="mistral", help="Ex: llama3, mistral")
        st.caption("Certifique-se de que o 'ollama serve' está rodando.")
    elif llm_provider == "Nuvem (Gemini)":
        api_key = st.text_input("Gemini API Key:", type="password", help="Obtenha grátis em aistudio.google.com")
        if not api_key: st.warning("Insira a chave para usar.")

    st.divider()
    
    # --- FILTROS ---
    st.subheader("Filtros & Limites")
    max_professors = st.slider("Máx. Resultados", 1, 20, 5)
    max_pubs_limit = st.slider("Máx. Publicações (Detalhes)", 1, 10, 3)
    
    st.divider()
    
    # --- FAVORITOS ---
    st.subheader(f"⭐ Favoritos ({len(st.session_state.favorites)})")
    if st.session_state.favorites:
        for fav_id, fav_data in list(st.session_state.favorites.items()):
            c1, c2 = st.columns([4, 1])
            # Nome vira botão para ver detalhes
            if c1.button(fav_data['nome'], key=f"nav_fav_{fav_id}"):
                view_professor_details(fav_data)
            
            # Botão X para remover
            if c2.button("✕", key=f"rm_fav_{fav_id}"):
                 del st.session_state.favorites[fav_id]
                 st.rerun()
    else:
        st.caption("Nenhum favorito ainda.")

    # --- BLACKLIST (OCULTOS) ---
    if st.session_state.blacklist:
        with st.expander(f"🚫 Ocultados ({len(st.session_state.blacklist)})"):
             for black_id, black_data in list(st.session_state.blacklist.items()):
                c1, c2 = st.columns([4, 1])
                c1.text(black_data['nome'])
                if c2.button("↺", key=f"rst_{black_id}", help="Restaurar"):
                    del st.session_state.blacklist[black_id]
                    st.rerun()

# --------------------------------------------------------------------------- #
#       INTERFACE PRINCIPAL                                                   #
# --------------------------------------------------------------------------- #

st.title("Encontre seu Orientador Ideal")

# --- MODO DE VISUALIZAÇÃO ÚNICA (DETALHES) ---
if st.session_state.view_mode == "single_view" and st.session_state.selected_prof:
    prof = st.session_state.selected_prof
    
    # Botão de Voltar
    if st.button("← Voltar para a busca"):
        back_to_search()
        
    with st.container(border=True):
        st.header(prof['nome'])
        st.caption(f"Score Total: **{prof['hybrid_score']:.2f}**")
        
        # Explicação Detalhada da IA
        query = st.session_state.refined_query or "sua pesquisa"
        explanation = llm_explain_recommendation(prof['nome'], prof['hybrid_score'], query, llm_provider, ollama_model, api_key)
        st.info(explanation)
        
        # Detalhes das Métricas (JSON Raw)
        with st.expander("Ver Detalhes do Cálculo (Debug)"):
            st.json(prof.get('details', {}))
        
        st.subheader("Publicações Detalhadas")
        # Busca mais publicações no modo detalhe (até 10)
        with st.spinner("Carregando publicações..."):
            pubs, total = get_publications_by_professor_id(prof['id'], limit=10)
            if pubs:
                st.write(f"Mostrando as 10 mais recentes de {total} encontradas:")
                for p in pubs:
                    st.markdown(f"- {p}")
            else:
                st.warning("Nenhuma publicação encontrada no banco de dados.")
            
    # Botões de Ação no modo Detalhe
    c1, c2 = st.columns(2)
    is_fav = prof['id'] in st.session_state.favorites
    
    if c1.button("★ Remover Favorito" if is_fav else "☆ Favoritar", key="det_fav", use_container_width=True, type="primary" if is_fav else "secondary"):
        toggle_favorite(prof)
        st.rerun()
        
    if c2.button("🚫 Ocultar Professor", key="det_blk", use_container_width=True):
        toggle_blacklist(prof)
        back_to_search()

# --- MODO DE BUSCA (PADRÃO) ---
else:
    # Histórico de Chat
    if st.session_state.search_history:
        with st.expander("Ver histórico da conversa", expanded=False):
            for msg in st.session_state.search_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    # Input do Usuário
    if prompt := st.chat_input("Ex: Pesquisar sobre Inteligência Artificial aplicada à saúde..."):
        
        st.session_state.search_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.status("🔍 Analisando...", expanded=True) as status:
            # 1. Refinamento de Query com IA
            st.write(f"Refinando busca com {llm_provider}...")
            refined_query = llm_refine_query(prompt, llm_provider, ollama_model, api_key)
            st.session_state.refined_query = refined_query
            st.write(f"Termos técnicos identificados: *{refined_query}*")
            
            st.write("Consultando Motor de Recomendação (Tese)...")
            
            try:
                # 2. Busca no Motor Principal (Passando os pesos customizados)
                results = thesis_recommendation_engine(refined_query, False, weights)
                
                # Filtragem de blacklist (não mostra quem foi ocultado)
                valid_results = [r for r in results if r['id'] not in st.session_state.blacklist]
                st.session_state.current_results = valid_results
                
                status.update(label="Busca concluída!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Erro na busca", state="error")
                st.error(f"Erro no motor de recomendação: {e}")
                st.code(traceback.format_exc())
                st.session_state.current_results = []

    # --- ÁREA DE RESULTADOS (PERSISTENTE) ---
    if st.session_state.current_results:
        
        st.divider()
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

            # --- CARD UNIFICADO ---
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                
                # Coluna Esquerda: Informações
                with c1:
                    st.markdown(f"### {prof['nome']}")
                    
                    # --- BREAKDOWN DO CÁLCULO ---
                    det = prof.get('details', {})
                    # Monta string explicativa resumida com TODAS as variáveis
                    formula_parts = []
                    
                    # Ordem lógica sugerida na tese: Area, Exp, Prod, Efi, Colab, Pesq, Qual
                    if w_area > 0: formula_parts.append(f"Area:1.0") # Sempre 1.0 se retornou
                    if w_exp > 0: formula_parts.append(f"Exp:{det.get('raw_exp',0):.1f}")
                    if w_prod > 0: formula_parts.append(f"Prod:{det.get('raw_prod',0):.1f}")
                    if w_efi > 0: formula_parts.append(f"Efi:{det.get('raw_efi',0):.1f}")
                    if w_colab > 0: formula_parts.append(f"Colab:{det.get('raw_colab',0):.1f}")
                    
                    # Pesquisa é derivada de produção (0.5x) se não vier no details
                    val_pesq = det.get('raw_pesq', det.get('raw_prod', 0) * 0.5)
                    if w_pesq > 0: formula_parts.append(f"Pesq:{val_pesq:.1f}")
                    
                    if w_qual > 0: formula_parts.append(f"Qual:{det.get('raw_qual',0):.1f}")
                    
                    formula_str = " | ".join(formula_parts)
                    st.markdown(f"<div class='score-breakdown'>📊 Métricas: {formula_str} -> <span class='score-val'>Score Final: {prof['hybrid_score']:.2f}</span></div>", unsafe_allow_html=True)
                    
                    # Explicação IA
                    if 'refined_query' in st.session_state:
                         explanation = llm_explain_recommendation(prof['nome'], prof['hybrid_score'], st.session_state.refined_query, llm_provider, ollama_model, api_key)
                         st.info(explanation)

                    with st.expander("Ver publicações recentes"):
                        pubs, _ = get_publications_by_professor_id(prof['id'], limit=max_pubs_limit)
                        if pubs:
                            for p in pubs: st.text(f"• {p}")
                        else:
                            st.caption("Nenhuma publicação encontrada.")

                # Coluna Direita: Ações Verticais
                with c2:
                    st.write("") # Espaçamento superior para alinhar
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
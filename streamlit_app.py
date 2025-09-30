# streamlit_app.py - Interface principal com Streamlit
import streamlit as st
import pandas as pd
import traceback

# Funções do projeto
from dataset_generator import generate_mock_dataset
from recommend import recommend_with_tfidf
from db_utils import get_professors_data
from chroma_utils import sync_postgres_to_chroma, get_all_professors_from_chroma # Novas importações

# --- Configuração da Página ---
st.set_page_config(page_title="RecomendaProf", layout="wide", initial_sidebar_state="expanded")

# --- Cabeçalho ---
st.title("🎓 RecomendaProf")
st.write("Um chatbot para recomendação de orientadores de mestrado e doutorado com base na sua área de pesquisa.")

# --- Barra Lateral (Sidebar) ---
st.sidebar.title("Configurações")
data_source = st.sidebar.selectbox("Fonte de dados", ["Mock (apresentação)", "Banco de dados real"])

st.sidebar.info("Este projeto utiliza TF-IDF e Similaridade de Cossenos para encontrar os orientadores mais alinhados à sua pesquisa.")

# --- Nova Seção: Gerenciamento de Dados ---
if data_source == "Banco de dados real":
    st.sidebar.title("Gerenciamento de Dados")
    st.sidebar.write("Como o banco de dados real (PostgreSQL) pode ser lento para consultas repetidas, usamos um cache local (ChromaDB) para acelerar as recomendações.")
    
    if st.sidebar.button("Sincronizar PostgreSQL ➔ ChromaDB"):
        try:
            with st.spinner("Buscando dados do PostgreSQL e salvando no ChromaDB..."):
                count = sync_postgres_to_chroma()
            st.sidebar.success(f"{count} orientador(es) sincronizados com sucesso!")
            st.toast("Sincronização concluída!", icon="✅")
        except Exception as e:
            st.sidebar.error("Falha na sincronização.")
            st.toast("Erro ao sincronizar.", icon="❌")
            # Mostra o erro detalhado no app principal para depuração
            st.error(f"Detalhes do erro de sincronização: {e}")


# --- Inputs do Usuário ---
st.header("Qual é o seu interesse de pesquisa?")
student_area = st.text_input(
    "Digite as palavras-chave da sua área de pesquisa:",
    "Redes neurais para processamento de imagens médicas"
)

student_text_details = st.text_area(
    "Se quiser, descreva um pouco mais sobre seu projeto (opcional):",
    "Meu foco é utilizar deep learning, especificamente redes convolucionais, para detectar anomalias em exames de ressonância magnética.",
    height=100
)

recommend_button = st.button("Recomender Orientadores")

# --- Lógica de Recomendação ---
if recommend_button:
    if not student_area:
        st.error("Por favor, digite sua área de pesquisa.")
    else:
        results = []
        if data_source == "Mock (apresentação)":
            st.info("Executando em modo de demonstração com dados fictícios.")
            with st.spinner("Gerando dados e calculando recomendações..."):
                professors_df = generate_mock_dataset()
                professors_list = professors_df.to_dict(orient="records")
                results = recommend_with_tfidf(student_area, professors_list)

        else: # "Banco de dados real"
            st.info("Buscando orientadores a partir do cache local (ChromaDB)...")
            with st.spinner("Lendo dados e calculando recomendações..."):
                try:
                    # Busca os dados dos professores do ChromaDB
                    professors_list = get_all_professors_from_chroma()
                    if not professors_list:
                         st.warning("Nenhum orientador encontrado no cache local. Sincronize os dados na barra lateral.")
                    else:
                        results = recommend_with_tfidf(student_area, professors_list)

                except Exception as e:
                    st.error("Falha ao ler dados do ChromaDB.")
                    st.error("Certifique-se de que os dados foram sincronizados e o ChromaDB está acessível.")
                    with st.expander("Detalhes do Erro"):
                        st.code(traceback.format_exc())

        # --- Exibição dos Resultados ---
        st.header("Resultados da Recomendação")
        if results:
            st.success(f"Encontramos {len(results)} orientador(es) com alta afinidade:")
            # Criando colunas para um layout mais limpo
            num_cols = len(results) if len(results) <= 3 else 3
            cols = st.columns(num_cols)
            for i, r in enumerate(results):
                with cols[i % num_cols]:
                    st.markdown(f"### {r['name']}")
                    st.markdown(f"**Afinidade:** `{r['percent']}%`")
                    st.markdown(f"**Linha de Pesquisa:**")
                    st.caption(f"{r['research']}")
        else:
            st.warning("Nenhum orientador com afinidade suficiente foi encontrado para a área de pesquisa informada.")


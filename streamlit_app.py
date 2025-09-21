# streamlit_app.py - Interface principal com Streamlit
import streamlit as st
import pandas as pd
from dataset_generator import generate_mock_dataset
from recommend import recommend_with_tfidf

st.set_page_config(page_title="RecomendaProf", layout="wide")

st.title("🎓 RecomendaProf")
st.write("Chatbot de recomendação de orientadores para mestrado/doutorado.")

use_mock = st.sidebar.selectbox("Fonte de dados", ["Mock (apresentação)", "Banco de dados real"])

student_area = st.text_input("Área de pesquisa desejada", "Redes neurais")
student_text = st.text_area("Resumo do projeto / interesses", "Quero estudar aprendizado de máquina aplicado a visão computacional.")

if use_mock == "Mock (apresentação)":
    st.info("Rodando em modo demonstração com dados mockados.")
    df = generate_mock_dataset()
    if st.button("Recomendar"):
        results = recommend_with_tfidf(student_area, df.to_dict(orient="records"))
        if results:
            st.subheader("Professores recomendados:")
            for r in results:
                st.markdown(f"**{r['name']}** — {r['research']} (Recomendação: {r['percent']}%)")
        else:
            st.warning("Nenhum professor encontrado com afinidade suficiente.")
else:
    st.warning("Integração real com banco ainda não configurada. Use o modo Mock.")

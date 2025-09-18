# 🎓 RecomendaProf

RecomendaProf é um **chatbot para recomendação de orientadores de mestrado/doutorado**.  
Ele utiliza informações extraídas do **Currículo Lattes**, métricas de impacto de publicações (DOI, Impact Factor, CiteScore), e um modelo matemático em **Scikit-learn** para recomendar o professor mais adequado para um aluno de acordo com sua área de pesquisa.

O projeto está sendo reimplementado em **Python** com **Streamlit** para interface gráfica, **ChromaDB** como banco de embeddings vetoriais, e possibilidade de integração com **PostgreSQL**.

---

## 🚀 Funcionalidades

- Upload e processamento de currículos Lattes (extração automática de publicações e DOIs).
- Geração de datasets a partir das informações extraídas.
- Classificação e ranqueamento de professores de acordo com sua relevância.
- Chatbot interativo para consulta dos melhores orientadores por área.
- **Modo Mock**: permite rodar o sistema mesmo sem banco de dados real, ideal para apresentações e demonstrações.

---

## 📂 Estrutura do Projeto

```
.
├── ingest.py              # Conversão do ProcessadorLattesCompleto.java
├── recommend.py           # Conversão do ProcessadorQualis.java
├── dataset_generator.py   # Conversão do GeradorDeDatasets.java
├── streamlit_app.py       # Interface em Streamlit (menu mock/real incluído)
├── servidor-unificado.py  # Backend legado
├── create_tables.sql      # Estrutura de tabelas no PostgreSQL
├── ProcessadorLattesCompleto.java  # Código original em Java
├── ProcessadorQualis.java           # Código original em Java
├── GeradorDeDatasets.java           # Código original em Java
├── requirements.txt       # Dependências do projeto
└── README.md              # Documentação
```

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** – interface web
- **Pandas** – manipulação de datasets
- **NumPy** – operações matemáticas
- **Scikit-learn** – modelo de recomendação
- **BeautifulSoup4 + lxml** – parsing do Lattes (HTML/XML)
- **ChromaDB** – banco vetorial para embeddings
- **PostgreSQL** – armazenamento estruturado
- **Requests** – integração externa (ex. CrossRef)

---

## ⚙️ Instalação

1. Clone este repositório ou extraia o `.zip`:
   ```bash
   unzip projeto_completo_com_python.zip
   cd projeto_completo_com_python
   ```

2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

---

## ▶️ Como Rodar

### 1. Rodar em modo **Mock (apresentação)**
Esse modo não precisa de banco de dados e funciona com exemplos fictícios.

```bash
streamlit run streamlit_app.py
```

- No menu lateral do Streamlit, escolha: **Fonte de dados → Mock (apresentação)**  
- Digite a área de pesquisa desejada (ex: "Redes neurais")  
- Clique em **Recomendar** para ver os professores simulados.

### 2. Rodar em modo **Banco de dados real**
Esse modo conecta ao PostgreSQL/ChromaDB (ainda em implementação).

- Configure seu banco PostgreSQL com o script `create_tables.sql`  
- Configure as credenciais no `servidor-unificado.py`  
- Rode o app com:  
  ```bash
  streamlit run streamlit_app.py
  ```
- Escolha no menu lateral: **Fonte de dados → Banco de dados real**

⚠️ Observação: o modo real está planejado para integração futura, mas já possui a estrutura básica pronta.

---

## 📊 Modo Mock vs Real

- **Mock** → Útil para apresentações/demonstrações, usa dados simulados (`dataset_generator.py`).
- **Real** → Conecta ao banco PostgreSQL e processa currículos Lattes.

---

## 👩‍💻 Autoria

Este projeto é parte de uma pesquisa de doutorado e está em desenvolvimento contínuo.  
A lógica matemática do modelo em **Scikit-learn** é fixa (não pode ser alterada), enquanto os demais módulos foram reimplementados em Python.

---

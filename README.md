# 🎓 RecomendaProf

RecomendaProf é um **chatbot para recomendação de orientadores de mestrado/doutorado**.  
Ele utiliza informações extraídas do **Currículo Lattes**, métricas de impacto de publicações (DOI, Impact Factor, CiteScore), e um modelo matemático em **Scikit-learn** com uma abordagem híbrida, combinando busca semântica vetorial com métricas de produtividade para recomendar o professor mais adequado para um aluno de acordo com sua área de pesquisa.

---

O projeto está sendo reimplementado em **Python** com **Streamlit** para interface gráfica, **ChromaDB** como banco de embeddings vetoriais, e possibilidade de integração com **PostgreSQL**.

---

## 🖼️ Imagem do projeto rodando
![Exemplo do projeto rodando com dados mockados](assets/example_mockeddata.png)

---

## 🔍 Como funciona a recomendação?

O sistema calcula um **Score de Afinidade** para cada orientador com base em dois pilares:

1.  **Busca Semântica (Similaridade de Tema)**
    - O texto do projeto ou área de interesse do aluno é convertido em um embedding vetorial.
    - Utilizando o **ChromaDB**, o sistema busca os professores cujas publicações (agregadas em um único documento por professor) são semanticamente mais próximas do texto do aluno. A "distância" entre os vetores é usada para calcular a similaridade.

2.  **Score de Produtividade (Métricas Acadêmicas)**
    - Métricas como número de publicações, número de orientações concluídas e o score médio de Qualis das publicações são coletadas para cada professor.
    - Esses valores são normalizados e combinados para gerar um único score de produtividade.

O **Score Híbrido** final é uma média ponderada entre a similaridade semântica e o score de produtividade, resultando em uma recomendação balanceada que considera tanto a afinidade de tema quanto a experiência e produção acadêmica do orientador.

---

## 🚀 Funcionalidades

- Upload e processamento de currículos Lattes (extração automática de publicações e DOIs).
- Geração de datasets a partir das informações extraídas.
- Classificação e ranqueamento de professores de acordo com sua relevância.
- Chatbot interativo para consulta dos melhores orientadores por área.

---

## 📂 Estrutura do Projeto

```
.
├── chroma_utils.py        # Utilitário para coisas banco de dados ChromaDB
├── db_utils.py            # Utilitário para coisas bando de dados PostgreSQL
├── recommend_chroma.py    # Motor de recomendação adaptada ao ChromaDB
├── streamlit_app.py       # Interface em Streamlit
├── requirements.txt       # Dependências do projeto
├── README.md              # Documentação
│
├── legacy/
│   ├── ingest.py              # Script legado de extração de informações de currículos lattes (é usado os dados já no banco de dados para isso)
│   ├── recommend.py           # Algoritmo de recomendação que usava informações do PostgreSQL
│   └── dataset_generator.py   # Script para criação de dados mockados simples (incompatíveis com o código atual pelo quão simples são)
│
│
├── legacy_java/
│   ├── ProcessadorLattesCompleto.java # Código original em Java
│   ├── ProcessadorQualis.java         # Código original em Java
│   └── GeradorDeDatasets.java         # Código original em Java
│
├── sql/
│   └── create_tables.sql # Estrutura de tabelas no PostgreSQL
│
├── utils/
│   └── servidor-unificado.py # Backend legado
│
└── assets/
    └── exemplo.png
```

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** – Para a interface web interativa.
- **ChromaDB** – Banco de dados vetorial para busca de similaridade.
- **PostgreSQL** – Banco de dados relacional para os dados brutos.
- **Pandas** – Para manipulação e processamento de dados.
- **Psycopg2** – Driver de conexão com o PostgreSQL.

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

### 1. Rodar em modo **Banco de dados real**
Esse modo conecta ao PostgreSQL/ChromaDB.

- Crie as tables de seu banco PostgreSQL com o script `create_tables.sql`
- Configure as credenciais no `db_utils.py`  
- Rode o app com:  
  ```bash
  streamlit run streamlit_app.py
  ```
- Se certifique de ter dados suficientes no banco PostgreSQL
- Clique no botão no menu lateral: "Sincronizar PosgreSQL -> ChromaDB"
- Aparecerá um alerta em verde caso tenha sucesso na sincronização
- Digite a área de pesquisa desejada (ex: "Redes neurais")
- Clique em **Recomendar** para ver os professores simulados.

---

## 👩‍💻 Autoria

Este projeto é parte de uma pesquisa de doutorado e está em desenvolvimento contínuo.  
A lógica matemática do modelo em **Scikit-learn** é fixa (não pode ser alterada), enquanto os demais módulos foram reimplementados em Python.

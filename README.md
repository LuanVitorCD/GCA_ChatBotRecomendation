# 🎓 RecomendaProf

**RecomendaProf** é um sistema inteligente de recomendação de orientadores de pós-graduação (Mestrado e Doutorado), desenvolvido como implementação prática de uma Tese de Doutorado em Ciência da Computação.
O sistema utiliza uma abordagem híbrida que combina **Processamento de Linguagem Natural (PLN), Clustering (Agrupamento)** e **Modelagem Matemática** para identificar e ranquear docentes com base na afinidade temática e produtividade acadêmica.

---

## 💡 Visão Geral

O sistema utiliza dados extraídos do **Currículo Lattes**, além de métricas de impacto (DOI, Impact Factor, CiteScore).  
A aplicação foi reimplementada com **Streamlit** para interface gráfica, **ChromaDB** como banco vetorial e integração com **PostgreSQL**.

---

## 🖼️ Imagem do projeto rodando
![Exemplo do projeto rodando com dados reais no motor moderno](assets/example_llmassisted_chatresults.png)

---

## ✨ Principais Funcionalidades
- Motor de Recomendação Validado: Implementação fiel do algoritmo de clustering (Birch/KMeans) e ranking ponderado descrito na metodologia da tese.

- Assistente de IA (Cérebro Duplo):
   - Refinamento de Busca: Transforma a linguagem natural do aluno (ex: "quero estudar cura do câncer") em termos técnicos acadêmicos otimizados para a busca Lattes.
   - Explicações Personalizadas: Gera justificativas em linguagem natural explicando por que aquele professor foi recomendado para você.
   - Suporte a Múltiplos Provedores: Funciona com Ollama (Local/Offline) para privacidade total ou Google Gemini via API.

- Interface Conversacional (Chatbot): Uma experiência de chat fluida para refinamento progressivo da pesquisa.

- Gestão de Candidatos:
   - ⭐ Favoritos: Salve perfis promissores para análise posterior;
   - 🚫 Blacklist: Oculte professores que não atendem aos seus critérios, limpando os resultados futuros;
   - 📄 Visualização Focada: Modo de detalhes para análise aprofundada de publicações.

---

## 🧠 Como Funciona a Recomendação

O sistema opera em um pipeline de 3 estágios:

1. **Filtragem & Clustering**
   - O input do aluno é processado por uma LLM (Llama 3, Mistral ou Gemini) que extrai o "núcleo semântico" da pesquisa.

2. **Produtividade Acadêmica**
   - O texto refinado é cruzado com a base de dados PostgreSQL;
   - Algoritmos de Clustering (Birch) agrupam professores com perfis de publicação similares;
   - Um segundo nível de K-Means refina o grupo para encontrar a vizinhança mais próxima.
3. **Ranking Matemático**
   - Um índice de recomendação (Score) é calculado para cada candidato do cluster final;
   - **Fórmula:** IR = (0,3 * Publicacoes) + (0,3 * Orientacoes) + (0,4 * Qualis)
   - O resultado é normalizado pelo tempo de doutoramento, garantindo justiça entre professores seniores e juniores.

---

## 🧩 Estrutura do Projeto

```bash
.
├── streamlit_app.py        # Interface principal em Streamlit
├── recommend_legacy.py     # Motor legado (SQL + clustering)
├── chroma_utils.py         # Sincronização PostgreSQL → ChromaDB
├── db_utils.py             # Conexão e utilidades do banco PostgreSQL
├── requirements.txt        # Dependências do projeto
│
├── data/
│   └── mestrado - 02_21 09_05   # Arquivo backup dump de um banco de dados PostgreSQL com dados prontos para usar no App
│
├── sql/
│   └── create_tables.sql   # Estrutura de tabelas no PostgreSQL
│
├── legacy/   # Pasta com códigos legados
├── legacy_java/   # Pasta com scripts Java relacionados a curriculos lattes e quallis
├── utils/    # Pasta com Backend legado (Flask)
└── assets/   # Pasta com todas as imagens do projeto
```

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** — interface web interativa
- **ChromaDB** — banco vetorial para embeddings
- **PostgreSQL** — banco relacional principal
- **spaCy** — processamento de linguagem natural
- **Pandas** — manipulação de dados
- **Scikit-learn** — cálculo de métricas e pontuações
- **Psycopg2** — conexão com PostgreSQL
- **Ollama** — LLM Local

---

## ⚙️ Instalação
Pré-requisitos
- Python 3.10+
- PostgreSQL (com a base lattes importada)
- (Opcional) Ollama instalado localmente para IA offline de usos ilimitados

1. Configuração do Ambiente
```bash
git clone https://github.com/LuanVitorCD/GCA_ChatBotRecomendation.git
cd GCA_ChatBotRecomendation

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt

python -m spacy download pt_core_news_md
```

2. Banco de Dados (PostgreSQL)
   1. Crie um banco de dados no PostgreSQL;
   2. Restaure o backup lcoalizado na pasta "data/" (ou execute o script dentro da pasta "sql/" chamado "create_tables.sql" para começar do zero);
   3. Configure suas credenciais no arquivo "db_utils.py".

3. Configuração da IA (Ollama) - Opcional
Para usar o modo local (gratuito e privado):
   1. Instale o [Ollama](https://ollama.com/);
   2. No terminal, baixe um modelo leve (ex: Mistral);
   ```bash
   ollama pull mistral
   ```
   3. Mantenha o servidor Ollama rodando (ollama serve).

4. Executando o App
```bash
streamlit run streamlit_app.py
```

---

## 👩‍💻 Autoria

Este projeto é a implementação computacional da Tese de Doutorado de **Radi Melo Martins**.
Desenvolvido e mantido por **Luan Vitor C. D.**


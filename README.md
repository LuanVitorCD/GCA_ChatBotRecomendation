# GCA\_ChatBotRecomendation

Este repositório contém um chatbot que interage com um modelo matemático para calcular um índice de recomendação personalizado com base nas entradas do usuário.

---

## 🔎 Descrição do Projeto

O objetivo deste projeto é construir um sistema interativo onde o usuário conversa com um chatbot capaz de:

1. Receber preferências ou consultas do usuário.
2. Processar essas informações por meio de um modelo matemático que gera um índice de recomendação.
3. Retornar ao usuário uma recomendação embasada e justificar os pesos e variáveis utilizadas.

O projeto é dividido em duas camadas:

- **Frontend** (interface de chat)
- **Backend** (cálculo do índice e orquestração do diálogo)

---

## 🚀 Tecnologias e Ferramentas

- **Python**
  - [Streamlit](https://streamlit.io/) para prototipagem rápida da interface web.
  - [FastAPI](https://fastapi.tiangolo.com/) (opcional) para expor endpoints REST em produção.
  - [Scikit‑learn](https://scikit-learn.org/) / [SciPy](https://www.scipy.org/) para algoritmos matemáticos.
  - [Pandas](https://pandas.pydata.org/) para manipulação de dados.
  - [NumPy](https://numpy.org/) para cálculos numéricos.
  - Modelos de embeddings ou LLM local (por exemplo, Llama) para enriquecer o diálogo.
- **JavaScript / TypeScript** (opcional)
  - [Next.js](https://nextjs.org/) ou React para uma interface customizável e escalável.
  - [Tailwind CSS](https://tailwindcss.com/) para estilo rápido e responsivo.
  - [Socket.IO](https://socket.io/) ou [WebSockets](https://developer.mozilla.org/docs/Web/API/WebSockets_API) para chat em tempo real.

---

## 📈 Possíveis Modelos Matemáticos

| Abordagem                             | Descrição                                                            | Quando usar                                       |
| ------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------- |
| Regressão Linear / Múltipla           | Calcula um score contínuo a partir de variáveis quantificáveis.      | Quando índices são lineares e bem definidos.      |
| Fuzzy Logic                           | Permite lidar com incertezas e graus de pertencimento.               | Quando preferências são subjetivas.               |
| Collaborative Filtering               | Recomendação baseada em similaridade entre usuários ou itens.        | Em cenários de itens e histórico de usuários.     |
| Content-Based Filtering               | Recomendação baseada nas características dos itens.                  | Quando há metadados ricos sobre itens.            |
| Matriz de Utilidade Ponderada         | Combina múltiplos critérios com pesos ajustáveis.                    | Para inserir variáveis de importâncias distintas. |
| Técnicas baseadas em Machine Learning | Árvores de decisão, Random Forest, SVM para predição de preferência. | Quando há dados históricos de feedback.           |

---

## ⚙️ Estrutura do Repositório

```text
GCA_ChatBotRecomendation/
│
├── app/                      # Código Streamlit (frontend minimalista)
│   ├── main.py               # Entrada da aplicação Streamlit
│   └── utils.py              # Funções auxiliares (pré-processamento)
│
├── backend/                  # API FastAPI (opcional para produção)
│   ├── server.py             # Endpoints REST
│   └── models.py             # Definição dos modelos matemáticos
│
├── models/                   # Armazenamento de artefatos de modelo (pickle, joblib)
│
├── data/                     # Dados de exemplo e schemas
│   └── sample_data.csv       # Exemplo de entradas para teste
│
├── tests/                    # Testes unitários com pytest
│
├── .gitignore
├── requirements.txt          # Dependências do Python
└── README.md
```

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

- Python 3.8+ instalado
- `pip` configurado

### Instalação

1. Clone o repositório:

   ```bash
   git clone https://github.com/LuanVitorCD/GCA_ChatBotRecomendation.git
   cd GCA_ChatBotRecomendation
   ```

2. Crie um ambiente virtual e instale dependências:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .\.venv\\Scripts\\activate  # Windows
   pip install -r requirements.txt
   ```

### Uso com Streamlit

```bash
streamlit run app/main.py
```

A interface ficará disponível em `http://localhost:8501`.

### Uso via API FastAPI (opcional)

```bash
uvicorn backend.server:app --reload
```

A API estará disponível em `http://localhost:8000`.

---

## 🧮 Modelo Matemático de Exemplo

No arquivo `backend/models.py` implementamos uma **Matriz de Utilidade Ponderada**:

```python
# Exemplo simplificado
def calcula_indice(dados: dict, pesos: dict) -> float:
    # dados: {'criterio1': valor1, 'criterio2': valor2, ...}
    # pesos: {'criterio1': peso1, ...}, soma dos pesos = 1
    score = sum(dados[k] * pesos.get(k, 0) for k in dados)
    return score
```

Você pode estender para regressão, ML ou lógica fuzzy conforme necessidade.

---

## 🤝 Contribuição

1. Fork este repositório
2. Crie uma branch: `git checkout -b feature/minha-feature`
3. Faça commit das suas alterações: `git commit -m 'Minha contribuição'`
4. Push para a branch: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.


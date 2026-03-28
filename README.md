# ui-langchain-eval

API FastAPI com um agente LangChain/LangGraph para SSMA, memória multi-turn e observabilidade via Langfuse.

## Visão geral

O projeto expõe um agente SSMA com dois modos de execução:

- `POST /invoke`: retorna a resposta completa
- `POST /stream`: retorna a resposta via SSE

O agente usa:

- `AzureChatOpenAI` como LLM
- Azure AI Search para RAG híbrido
- `MongoDBSaver` no CosmosDB for MongoDB vCore quando configurado
- `InMemorySaver` em desenvolvimento sem Cosmos
- Langfuse via `CallbackHandler()` quando as variáveis de ambiente estiverem presentes

## Stack

| Camada | Tecnologia |
|--------|-----------|
| LLM | Azure OpenAI (`AzureChatOpenAI`) |
| Orquestração | LangChain `create_agent` + LangGraph |
| RAG | Azure AI Search (busca vetorial + textual) |
| Memória | `MongoDBSaver` ou `InMemorySaver` |
| API | FastAPI + uvicorn |
| Streaming | Server-Sent Events |
| Observabilidade | Langfuse |
| Auth | Entra ID JWT ou usuário mock em dev |

## Estrutura

```text
src/
├── main.py
├── core/
│   ├── auth.py
│   └── config.py
├── routes/
│   └── chat.py
├── agents/
│   ├── __init__.py
│   ├── agent.py
│   ├── ssma.py
│   ├── middleware/
│   │   └── chat_persistence.py
│   └── prompts/
│       └── ssma.md
├── schemas/
│   └── chat.py
├── tools/
│   └── az_aisearch_rag.py
└── utils/
    └── setup_db.py
```

## Como funciona

### Agente

`src/agents/agent.py` encapsula a criação e execução do agente. O `thread_id` e o `user_id` são passados por chamada, não no construtor.

```python
from src.agents.agent import Agent

agent = Agent(
    system_prompt="Você é...",
    tools=[minha_tool],
    name="MeuAgente",
)

answer = agent.invoke(
    "Olá",
    thread_id="user-123_chat-abc",
    user_id="user-123",
)
```

Para streaming:

```python
async for chunk in agent.astream(
    "Olá",
    thread_id="user-123_chat-abc",
    user_id="user-123",
):
    print(chunk)
```

### Memória

- Se `COSMOS_CONN_STRING` estiver definido, o projeto usa `MongoDBSaver`
- Se não estiver, usa `InMemorySaver`
- Na API, o agente é singleton por processo, então o histórico em memória persiste entre requests enquanto o processo estiver vivo

### Observabilidade

Quando `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` estão disponíveis no ambiente, o projeto adiciona `CallbackHandler()` no `config` do LangChain e popula `metadata` com:

- `langfuse_session_id`
- `langfuse_user_id`
- `langfuse_tags`

## API

### Endpoints

| Método | Path | Descrição |
|--------|------|-----------|
| `GET` | `/` | Healthcheck simples |
| `POST` | `/invoke` | Resposta completa |
| `POST` | `/stream` | Resposta via SSE |

### Body de chat

```json
{
  "message": "O que é NR-35?",
  "chat_id": "opcional"
}
```

### Resposta de `/invoke`

```json
{
  "chat_id": "verify-route-invoke",
  "thread_id": "user-dev-user_chat-verify-route-invoke",
  "answer": "..."
}
```

### Eventos de `/stream`

```text
event: meta
data: {"chat_id":"...","thread_id":"..."}

event: message
data: {"text":"chunk"}

event: done
data: {}
```

### Auth

Com `AUTH_ENABLED=false`, a API usa um usuário mock:

- `oid`: `dev-user`
- `name`: `Dev User`
- `email`: `dev@localhost`

Com `AUTH_ENABLED=true`, a API valida o bearer token do Entra ID usando o `oid` do JWT como `user_id`.

## Variáveis de ambiente

Veja `.env.example` para o conjunto completo. As principais são:

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `AZURE_OPENAI_ENDPOINT` | sim | Endpoint do Azure OpenAI |
| `AZURE_OPENAI_API_KEY` | sim | Chave do Azure OpenAI |
| `AZURE_OPENAI_API_VERSION` | sim | Versão da API |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | sim | Deployment do chat model |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | não | Deployment de embeddings |
| `AZURE_SEARCH_ENDPOINT` | sim | Endpoint do Azure AI Search |
| `AZURE_SEARCH_API_KEY` | sim | Chave do Azure AI Search |
| `COSMOS_CONN_STRING` | não | Habilita memória persistente |
| `COSMOS_DB` | não | Nome do banco no Cosmos |
| `LANGFUSE_PUBLIC_KEY` | não | Public key do Langfuse |
| `LANGFUSE_SECRET_KEY` | não | Secret key do Langfuse |
| `LANGFUSE_BASE_URL` | não | URL do Langfuse |
| `AUTH_ENABLED` | não | `false` em dev para usar usuário mock |
| `AZURE_AD_TENANT_ID` | se auth | Tenant do Entra ID |
| `AZURE_AD_CLIENT_ID` | se auth | Client ID da app registration |

Observação: `.env.example` também inclui variáveis de LangSmith, mas o fluxo principal atual do projeto está centrado em Langfuse.

## Executar

### Local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### Docker

```bash
docker compose up --build
```

No `docker-compose.yml`, `AUTH_ENABLED=false` já vem configurado para facilitar testes locais.

### Setup do CosmosDB

Se for usar memória persistente, crie os índices uma vez:

```bash
source .venv/bin/activate
python -m src.utils.setup_db
```

## Exemplos de uso

### `invoke`

```bash
curl -X POST http://127.0.0.1:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"message":"O que é NR-35?","chat_id":"chat-demo"}'
```

### `stream`

```bash
curl -N -X POST http://127.0.0.1:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"O que é NR-35?","chat_id":"chat-demo"}'
```

Se `AUTH_ENABLED=true`, inclua `Authorization: Bearer <token>`.

## Notebook de avaliação

O notebook `notebooks/langfuse.ipynb` serve para validar o agente localmente e inspecionar traces com mais facilidade.

Exemplo atualizado:

```python
ssma = Agent(
    system_prompt=(_prompts_dir / "ssma.md").read_text().strip(),
    tools=[rag_tool],
    name="SSMA",
)

ssma.invoke("O que é NR-35?", thread_id="ssma-001")
```

Para streaming no notebook:

```python
async for chunk in ssma.astream("O que é NR-35?", thread_id="ssma-stream-001"):
    print(chunk, end="", flush=True)
```

As tools do notebook são definidas inline com `@tool`, enquanto a lógica de busca pura fica em `notebooks/az_aisearch_rag.py`.

## Adicionar um novo agente

1. Crie um prompt em `src/agents/prompts/`
2. Crie uma factory em `src/agents/`
3. Reutilize `Agent(...)` com as tools e middleware necessários
4. Instancie o agente em `src/agents/__init__.py`

Exemplo mínimo:

```python
from pathlib import Path

from src.agents.agent import Agent
from src.tools.az_aisearch_rag import AzureRAG


def create_meu_agente(checkpointer=None, db=None) -> Agent:
    rag = AzureRAG(index_name="meu-index")
    return Agent(
        system_prompt=(Path(__file__).parent / "prompts" / "meu_agente.md").read_text().strip(),
        tools=[rag.as_tool()],
        checkpointer=checkpointer,
        name="MeuAgente",
    )
```

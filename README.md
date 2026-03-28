# ui-langchain-eval

Agente LangChain com API FastAPI, memória multi-turn no CosmosDB e observabilidade via Langfuse.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| LLM | Azure OpenAI (`AzureChatOpenAI`, deployment configurável) |
| Framework | LangChain `create_agent` + LangGraph |
| Memória | `MongoDBSaver` → CosmosDB for MongoDB vCore (ou `InMemorySaver` em dev) |
| API | FastAPI + uvicorn — SSE streaming e batch |
| Observabilidade | Langfuse (`CallbackHandler` + `propagate_attributes`) |
| Auth | Entra ID JWT (`oid` claim) — desabilitável com `AUTH_ENABLED=false` |
| RAG | Azure AI Search (busca híbrida vetorial + full-text) |

## Estrutura

```
src/
├── main.py                        # Entrypoint FastAPI + lifespan
├── core/
│   ├── config.py                  # Settings com @lru_cache
│   └── auth.py                    # Entra ID JWT ou mock dev
├── routes/
│   └── chat.py                    # POST /stream, POST /invoke
├── agents/
│   ├── agent.py                   # Classe Agent (DI completo, Langfuse encapsulado)
│   ├── ssma.py                    # create_ssma_agent() → Agent
│   ├── __init__.py                # Bootstrap Cosmos + instância singleton
│   ├── middleware/
│   │   └── chat_persistence.py    # ChatPersistenceHooks (before/after_agent → CosmosDB)
│   └── prompts/
│       └── ssma.md                # System prompt do agente SSMA
├── tools/
│   └── az_aisearch_rag.py         # AzureRAG — busca híbrida no Azure AI Search
├── schemas/
│   └── chat.py                    # MessageRequest, BatchResponse, ChatSummary
└── utils/
    └── setup_db.py                # Script one-off: cria índices no CosmosDB
```

## Classe Agent

O coração da aplicação. Recebe tudo via `__init__` — sem globals, sem acoplamento:

```python
from src.agents.agent import Agent, make_llm

agent = Agent(
    system_prompt="Você é...",
    tools=[minha_tool],
    llm=make_llm(),           # opcional — cria automaticamente se omitido
    checkpointer=checkpointer, # opcional — InMemorySaver se omitido
    middleware=[ChatPersistenceHooks(db)],  # opcional
    name="MeuAgente",
)

# FastAPI: thread_id e user_id por chamada (multi-tenant)
resposta = agent.invoke("Olá", thread_id="user-123_chat-abc", user_id="user-123")

# SSE streaming
async for chunk in agent.astream("Olá", thread_id="...", user_id="..."):
    yield chunk
```

O Langfuse (`propagate_attributes` + `CallbackHandler` + `flush`) é gerenciado internamente — ativado automaticamente quando `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` estiverem definidos.

## Adicionar um novo agente

1. Crie `src/agents/prompts/meu_agente.md` com o system prompt
2. Crie `src/agents/meu_agente.py` com a factory:

```python
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

3. Instancie em `src/agents/__init__.py` passando o checkpointer e `db` já configurados.

## API

| Método | Path | Descrição |
|--------|------|-----------|
| `POST` | `/stream` | Resposta em tempo real via SSE |
| `POST` | `/invoke` | Resposta completa |

### Eventos SSE (`/stream`)

```
event: meta
data: {"chat_id": "...", "thread_id": "..."}

event: message
data: {"text": "chunk de texto"}

event: done
data: {}
```

### Body das requests de chat

```json
{
  "message": "O que é NR-35?",
  "chat_id": "uuid-existente-opcional"
}
```

## Variáveis de ambiente

Ver `.env.example` para a lista completa com descrições. Principais:

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `AZURE_OPENAI_ENDPOINT` | sim | URL do recurso Azure OpenAI |
| `AZURE_OPENAI_API_KEY` | sim | Chave de autenticação |
| `AZURE_OPENAI_API_VERSION` | sim | Versão da API (ex: `2025-03-01-preview`) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | sim | Nome do deployment (ex: `gpt-5-chat`) |
| `AZURE_SEARCH_ENDPOINT` | sim | URL do Azure AI Search |
| `AZURE_SEARCH_API_KEY` | sim | Chave do Azure AI Search |
| `COSMOS_CONN_STRING` | não | Memória persistente (MongoDB vCore). Se ausente, usa `InMemorySaver` |
| `COSMOS_DB` | não | Nome do banco (padrão: `langgraph`) |
| `LANGFUSE_SECRET_KEY` | não | Ativa observabilidade Langfuse |
| `LANGFUSE_BASE_URL` | não | URL do Langfuse (ex: `http://localhost:3000`) |
| `AUTH_ENABLED` | não | `false` para desabilitar JWT em dev (padrão: `true`) |
| `AZURE_AD_TENANT_ID` | se auth | Tenant ID do Entra ID |
| `AZURE_AD_CLIENT_ID` | se auth | Client ID do app registration |

## Executar

```bash
# Dev local
cp .env.example .env  # preencha os valores
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

```bash
# Dev com Docker (AUTH_ENABLED=false automático)
docker compose up
```

```bash
# Setup índices CosmosDB (executar uma vez)
python -m src.utils.setup_db
```

## Notebook de avaliação

`notebooks/langfuse.ipynb` — testa o agente localmente com tracing completo.

Instancia agentes explicitamente com injeção de dependência:

```python
ssma = Agent(
    system_prompt=(_prompts_dir / "ssma.md").read_text().strip(),
    tools=[rag_tool],
    thread_id="ssma-001",
    user_id="andre@empresa.com",  # propagado ao Langfuse como user_id
    name="SSMA",
)
ssma.invoke("O que é NR-35?")
```

As tools com `@tool` são definidas inline no notebook para garantir que o `CallbackHandler` do Langfuse propague o tracing corretamente. A lógica pura (busca, embeddings) fica em `notebooks/tools.py`.

O tracing é encapsulado na classe `Agent`: `propagate_attributes(session_id=thread_id, user_id=user_id)` + `CallbackHandler()` + `flush()` — ativado automaticamente quando `LANGFUSE_SECRET_KEY` e `LANGFUSE_BASE_URL` estiverem definidos.
# ui-langchain-eval

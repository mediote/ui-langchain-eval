# ui-langchain-eval

Agente LangChain com API FastAPI, memória multi-turn no CosmosDB e autenticação via Entra ID.

## Instruções para Claude

### Antes de qualquer trabalho na API (rotas, auth, modelos, middleware HTTP)
Invocar o skill via MCP antes de escrever ou modificar código:
```
https://fastmcp.me/skills/details/868/fastapi-pro
```

### Antes de qualquer trabalho no agente (tools, hooks, middleware LangChain, memória, streaming)
Invocar os skills relevantes antes de escrever ou modificar código:
- `langchain-fundamentals` — `create_agent`, tools, streaming
- `langchain-middleware` — `wrap_tool_call`, hooks, HITL
- `langgraph-persistence` — checkpointer, thread_id, store
- `langgraph-fundamentals` — StateGraph, nodes, edges

## Estrutura

```
src/
├── main.py                          # Entrypoint FastAPI + lifespan
├── routes/
│   └── chat.py                      # POST /stream, POST /invoke
├── core/
│   ├── config.py                    # Settings (get_settings, @lru_cache)
│   └── auth.py                      # Entra ID JWT + mock dev (AUTH_ENABLED)
├── agents/
│   ├── agent.py                     # Classe Agent — DI completo, Langfuse encapsulado
│   ├── ssma.py                      # create_ssma_agent() → Agent
│   ├── __init__.py                  # Bootstrap Cosmos + instância singleton
│   ├── middleware/
│   │   └── chat_persistence.py      # ChatPersistenceHooks (before/after_agent → CosmosDB)
│   └── prompts/
│       └── ssma.md                  # System prompt do agente SSMA
├── tools/
│   └── az_aisearch_rag.py           # AzureRAG — busca híbrida (vetorial + keyword)
├── schemas/
│   └── chat.py                      # MessageRequest, BatchResponse, ChatSummary
└── utils/
    └── setup_db.py                  # Script one-off: cria índices no CosmosDB
```

## Stack

- **Framework**: LangChain interno (`create_agent`, `wrap_tool_call`) — requer `langchain>=1.2`
- **LLM**: Azure OpenAI (`AzureChatOpenAI`, deployment `gpt-5-chat`)
- **Memória short-term**: `MongoDBSaver` → CosmosDB for MongoDB vCore
- **API**: FastAPI + uvicorn, SSE streaming e batch
- **Auth**: Entra ID JWT (`oid` claim) — desabilitável com `AUTH_ENABLED=false`

## Variáveis de ambiente

Ver `.env.example` para lista completa. Principais:
- `AZURE_OPENAI_*` — LLM
- `AZURE_SEARCH_*` — RAG
- `COSMOS_CONN_STRING`, `COSMOS_DB` — memória
- `AZURE_AD_TENANT_ID`, `AZURE_AD_CLIENT_ID`, `AUTH_ENABLED` — auth

## Executar

```bash
# dev local
source .venv/bin/activate
uvicorn src.main:app --reload

# dev Docker (AUTH_ENABLED=false automático)
docker compose up
```

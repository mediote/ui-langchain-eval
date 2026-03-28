"""Classe Agent reutilizável com injeção de dependência completa."""

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.tools import BaseTool
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from src.core.config import get_settings


def make_llm() -> AzureChatOpenAI:
    s = get_settings()
    return AzureChatOpenAI(
        azure_deployment=s.azure_openai_deployment_name,
        api_version=s.azure_openai_api_version,
        api_key=s.azure_openai_api_key,
        azure_endpoint=s.azure_openai_endpoint,
        stream_usage=True,
    )


def _flush() -> None:
    if get_settings().langfuse_enabled:
        from langfuse import get_client

        get_client().flush()


class Agent:
    """Agente LangChain configurável via injeção de dependência.

    Parâmetros do construtor (todos via __init__, sem globals):
        system_prompt: Texto do prompt de sistema.
        tools: Lista de BaseTool para o agente.
        llm: Instância de AzureChatOpenAI. Se None, cria via make_llm().
        checkpointer: Checkpointer LangGraph. Se None, usa InMemorySaver().
        middleware: Lista de AgentMiddleware. Se None, sem middleware.
        name: Nome do agente (aparece nos traces).

    Na FastAPI thread_id e user_id são passados por chamada (multi-tenant).
    No notebook são passados no construtor (um Agent por sessão de teste).
    """

    def __init__(
        self,
        system_prompt: str,
        tools: list[BaseTool],
        llm: AzureChatOpenAI | None = None,
        checkpointer=None,
        middleware: list | None = None,
        name: str = "Agent",
    ) -> None:
        self._agent = create_agent(
            model=llm or make_llm(),
            tools=tools,
            system_prompt=system_prompt,
            name=name,
            checkpointer=checkpointer or InMemorySaver(),
            middleware=middleware or [],
        )

    def _build_config(self, thread_id: str, user_id: str) -> dict:
        config: dict = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        if get_settings().langfuse_enabled:
            from langfuse.langchain import CallbackHandler
            config["callbacks"] = [CallbackHandler()]
            config["metadata"] = {
                "langfuse_session_id": thread_id,
                "langfuse_user_id": user_id,
                "langfuse_tags": ["agent"],
            }
        return config

    def invoke(
        self, user_message: str, *, thread_id: str, user_id: str = "anonymous"
    ) -> str:
        """Retorna a resposta completa do agente (batch)."""
        try:
            result = self._agent.invoke(
                {"messages": [{"role": "user", "content": user_message}]},
                config=self._build_config(thread_id, user_id),
            )
        finally:
            _flush()
        messages = result.get("messages", [])
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        return last_ai.content if last_ai else ""

    async def astream(
        self, user_message: str, *, thread_id: str, user_id: str = "anonymous"
    ):
        """Gera chunks de texto da resposta (SSE / streaming)."""
        try:
            async for message, _ in self._agent.astream(
                {"messages": [{"role": "user", "content": user_message}]},
                config=self._build_config(thread_id, user_id),
                stream_mode="messages",
            ):
                if isinstance(message, AIMessageChunk) and message.content:
                    yield message.content
        finally:
            _flush()

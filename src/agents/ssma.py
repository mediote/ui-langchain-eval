"""Factory do agente SSMA."""
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from src.agents.agent import Agent
from src.agents.middleware import ChatPersistenceHooks
from src.tools import AzureRAG

def create_ssma_agent(checkpointer=None, db=None) -> Agent:
    rag = AzureRAG(
        index_name="shp-base-conhecimento-ssma-index",
        top_k=10,
        text_field="snippet",
        vector_field="snippet_vector",
        title_field="doc_url",
    )

    @tool
    def rag_tool(
        query: Annotated[str, "Pergunta ou termos de busca para consultar a base de conhecimento SSMA."],
    ) -> str:
        """Busca documentos na base de conhecimento. Use antes de responder ao usuário."""
        from langfuse import get_client
        with get_client().start_as_current_span(name="rag_tool", input={"query": query}) as span:
            result = rag.search(query)
            span.update(output=result[:500])
            return result

    middleware = []
    if db is not None:
        middleware.append(ChatPersistenceHooks(db))

    return Agent(
        system_prompt=(Path(__file__).parent / "prompts" / "ssma.md").read_text().strip(),
        tools=[rag_tool],
        checkpointer=checkpointer,
        middleware=middleware,
        name="SSMA",
    )

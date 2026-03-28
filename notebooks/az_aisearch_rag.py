"""Funções puras para uso nos notebooks — sem dependência de src.* e sem @tool."""

import logging
import os
from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def _search_client(index_name: str) -> SearchClient:
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=index_name,
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"]),
    )


def _embed(query: str) -> list[float]:
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT", os.environ["AZURE_OPENAI_ENDPOINT"]),
        api_version=os.environ.get("AZURE_OPENAI_EMBEDDING_API_VERSION", os.environ["AZURE_OPENAI_API_VERSION"]),
    )
    response = client.embeddings.create(model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"], input=query)
    return response.data[0].embedding


def rag(
    index_name: str,
    query: str,
    top_k: int = 5,
    text_field: str = "chunk",
    vector_field: str = "text_vector",
    title_field: str = "title",
) -> str:
    """Hybrid RAG: vector + keyword search no Azure AI Search."""
    vector = _embed(query)
    results = _search_client(index_name).search(
        search_text=query,
        vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=top_k, fields=vector_field)],
        top=top_k,
        select=list({text_field, title_field}),
    )
    parts = []
    for doc in results:
        chunk = str(doc.get(text_field) or "").strip()
        if chunk:
            title = doc.get(title_field) or ""
            parts.append(f"[{title}]\n{chunk}" if title else chunk)
    return "\n\n---\n\n".join(parts) if parts else "No results found."


def what_is_langfuse_info() -> str:
    return (
        "Langfuse é uma plataforma open source de observabilidade para aplicações LLM. "
        "Captura traces completos de agentes — inputs, outputs, latências, tokens e tool calls. "
        "Pode ser self-hosted (Docker/Kubernetes) ou usado via Langfuse Cloud. "
        "Integra nativamente com LangChain, LangGraph e OpenAI via callbacks ou @observe. "
        "Suporta LLM-as-a-judge, gerenciamento de prompts, datasets e sessões de usuário."
    )

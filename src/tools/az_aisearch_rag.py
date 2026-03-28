"""RAG tool via Azure AI Search (hybrid vector + keyword)."""

import logging
from typing import Annotated

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from langchain_core.tools import tool
from openai import AzureOpenAI

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class AzureRAG:
    """Hybrid RAG (vector + keyword) backed by Azure AI Search."""

    def __init__(
        self,
        index_name: str,
        top_k: int = 5,
        text_field: str = "chunk",
        vector_field: str = "text_vector",
        title_field: str = "title",
    ):
        self.index_name = index_name
        self.top_k = top_k
        self.text_field = text_field
        self.vector_field = vector_field
        self.title_field = title_field

        s = get_settings()
        self._search_client = SearchClient(
            endpoint=s.azure_search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(s.azure_search_api_key),
        )
        self._embed_client = AzureOpenAI(
            api_key=s.azure_openai_api_key,
            azure_endpoint=s.azure_openai_embedding_endpoint or s.azure_openai_endpoint,
            api_version=s.azure_openai_embedding_api_version or s.azure_openai_api_version,
        )
        self._embedding_deployment = s.azure_openai_embedding_deployment

    def _embed(self, query: str) -> list[float]:
        response = self._embed_client.embeddings.create(
            model=self._embedding_deployment, input=query
        )
        return response.data[0].embedding

    def search(self, query: str) -> str:
        """Executa hybrid search e retorna trechos formatados."""
        vector = self._embed(query)
        results = self._search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=self.top_k,
                    fields=self.vector_field,
                )
            ],
            top=self.top_k,
            select=list({self.text_field, self.title_field}),
        )
        parts = []
        for doc in results:
            chunk = str(doc.get(self.text_field) or "").strip()
            if chunk:
                title = doc.get(self.title_field) or ""
                parts.append(f"[{title}]\n{chunk}" if title else chunk)
        return "\n\n---\n\n".join(parts) if parts else "No results found."

    def as_tool(self):
        """Retorna uma BaseTool LangChain para uso nos agentes."""
        index_name = self.index_name

        @tool
        def rag_tool(
            query: Annotated[
                str,
                f"Pergunta ou termos de busca para consultar o índice {index_name}.",
            ],
        ) -> str:
            """Busca documentos na base de conhecimento. Use antes de responder ao usuário."""
            return self.search(query)

        return rag_tool

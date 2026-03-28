import os
from functools import lru_cache
from dataclasses import dataclass


@dataclass
class Settings:
    # LLM
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_deployment_name: str
    # Embeddings
    azure_openai_embedding_endpoint: str | None
    azure_openai_embedding_api_version: str | None
    azure_openai_embedding_deployment: str
    # Azure AI Search
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_top_k: int
    # Langfuse
    langfuse_secret_key: str | None
    langfuse_base_url: str | None

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_secret_key and self.langfuse_base_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        azure_openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_openai_deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        azure_openai_embedding_endpoint=os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
        azure_openai_embedding_api_version=os.environ.get("AZURE_OPENAI_EMBEDDING_API_VERSION"),
        azure_openai_embedding_deployment=os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        ),
        azure_search_endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        azure_search_api_key=os.environ["AZURE_SEARCH_API_KEY"],
        azure_search_top_k=int(os.environ.get("AZURE_SEARCH_TOP_K", "5")),
        langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        langfuse_base_url=os.environ.get("LANGFUSE_BASE_URL"),
    )

from datetime import datetime, timezone

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import AIMessage, HumanMessage
from langgraph.config import get_config
from pymongo.database import Database


class ChatPersistenceHooks(AgentMiddleware):
    """Hooks de ciclo de vida que registram o chat e salvam cada troca no CosmosDB."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def before_agent(self, state, runtime) -> None:
        """Registra o chat na collection 'chats' se ainda não existir."""
        config = get_config()["configurable"]
        thread_id = config.get("thread_id", "default")
        user_id = config.get("user_id", "anonymous")
        messages = state.get("messages", [])
        first_human = next((m for m in messages if isinstance(m, HumanMessage)), None)
        if first_human:
            self._db["chats"].update_one(
                {"thread_id": thread_id},
                {"$setOnInsert": {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "title": first_human.content[:60],
                    "created_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )

    def after_agent(self, state, runtime) -> None:
        """Salva a troca user/assistant após cada resposta."""
        thread_id = get_config()["configurable"].get("thread_id", "default")
        messages = state.get("messages", [])
        if len(messages) < 2:
            return
        last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        if last_human and last_ai:
            self._db["chats"].update_one(
                {"thread_id": thread_id},
                {"$push": {"messages": {
                    "user": last_human.content,
                    "assistant": last_ai.content,
                    "timestamp": datetime.now(timezone.utc),
                }}},
            )

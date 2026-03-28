"""Bootstrap do agente: conexão Cosmos (se configurada) e instância singleton."""
import os

from langgraph.checkpoint.memory import InMemorySaver

from src.agents.ssma import create_ssma_agent

mongo_client = None
db = None

if os.environ.get("COSMOS_CONN_STRING"):
    from pymongo import MongoClient
    from langgraph.checkpoint.mongodb import MongoDBSaver

    mongo_client = MongoClient(os.environ["COSMOS_CONN_STRING"])
    db = mongo_client[os.environ.get("COSMOS_DB", "langgraph")]
    _checkpointer = MongoDBSaver(client=mongo_client, db_name=db.name)
else:
    _checkpointer = InMemorySaver()

agent = create_ssma_agent(checkpointer=_checkpointer, db=db)

__all__ = ["agent", "db", "mongo_client"]

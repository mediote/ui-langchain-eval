"""Cria a collection 'chats' no CosmosDB com os índices necessários."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

load_dotenv()

client = MongoClient(os.environ["COSMOS_CONN_STRING"])
db = client[os.environ.get("COSMOS_DB", "langgraph")]

chats = db["chats"]

chats.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
chats.create_index([("thread_id", ASCENDING)], unique=True)

print("Collection 'chats' criada com sucesso.")
print(f"Indexes: {list(chats.index_information().keys())}")

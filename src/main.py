"""Entrypoint da API FastAPI."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # deve rodar antes de qualquer import LangChain/LangSmith

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from src.agents import mongo_client
    if mongo_client is not None:
        mongo_client.close()


app = FastAPI(
    title="SSMA Agent API",
    version="1.0.0",
    description="API do agente SSMA com suporte a SSE streaming e invoke.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}

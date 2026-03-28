"""Rotas de chat: SSE streaming e invoke."""
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.core.auth import UserInfo, get_current_user
from src.schemas.chat import BatchResponse, MessageRequest
from src.agents import agent

router = APIRouter(tags=["chat"])

CurrentUser = Annotated[UserInfo, Depends(get_current_user)]


def _resolve_thread(user_oid: str, chat_id: str | None) -> tuple[str, str]:
    """Retorna (chat_id, thread_id) — gera novo chat_id se não informado."""
    cid = chat_id or str(uuid.uuid4())
    tid = f"user-{user_oid}_chat-{cid}"
    return cid, tid


@router.post("/stream", summary="Chat com resposta em tempo real (SSE)")
async def chat_stream(body: MessageRequest, user: CurrentUser) -> StreamingResponse:
    """Resposta em tempo real via Server-Sent Events.

    Eventos:
    - `meta`: `{ chat_id, thread_id }` — enviado antes do primeiro chunk
    - `message`: `{ text }` — chunk de texto
    - `done`: fim da resposta
    """
    chat_id, thread_id = _resolve_thread(user.oid, body.chat_id)

    async def event_generator():
        yield f"event: meta\ndata: {json.dumps({'chat_id': chat_id, 'thread_id': thread_id})}\n\n"
        async for chunk in agent.astream(body.message, thread_id=thread_id, user_id=user.oid):
            yield f"event: message\ndata: {json.dumps({'text': chunk})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": chat_id,
        },
    )


@router.post("/invoke", response_model=BatchResponse, summary="Chat com resposta completa")
async def chat_invoke(body: MessageRequest, user: CurrentUser) -> BatchResponse:
    """Retorna a resposta completa do agente de uma vez."""
    chat_id, thread_id = _resolve_thread(user.oid, body.chat_id)
    answer = agent.invoke(body.message, thread_id=thread_id, user_id=user.oid)
    return BatchResponse(chat_id=chat_id, thread_id=thread_id, answer=answer)

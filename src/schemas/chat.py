from pydantic import BaseModel, ConfigDict


class MessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str
    chat_id: str | None = None  # None = novo chat


class BatchResponse(BaseModel):
    chat_id: str
    thread_id: str
    answer: str


class ChatSummary(BaseModel):
    chat_id: str | None = None
    thread_id: str
    user_id: str
    title: str

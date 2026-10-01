"""A StructuredLLMProvider that answers every show request with a scripted show."""

import json

from app.services.llm.base import ChatMessage, LLMError, StructuredLLMProvider

SUITABLE_SHOW = {
    "is_suitable": True,
    "decline_reason": "",
    "title": "Night Shift Abroad",
    "premise": "Two nurses swap stories about working far from home.",
    "topic": "living abroad as a nurse",
    "learner_role": "caller",
    "hosts": [
        {"name": "Florence", "personality": "storyteller", "angle": "Misses her home town."},
        {"name": "Mary", "personality": "dry_sceptic", "angle": "Thinks the pay is not worth it."},
    ],
}
DECLINED_SHOW = {
    **SUITABLE_SHOW,
    "is_suitable": False,
    "decline_reason": "The idea asks for instructions to hurt someone.",
}


class ScriptedShowLLM(StructuredLLMProvider):
    def __init__(self, reply: dict = SUITABLE_SHOW) -> None:
        self.reply = reply
        self.raw_reply: str | None = None
        self.error: LLMError | None = None
        self.calls: list[list[ChatMessage]] = []
        self.schemas: list[dict] = []

    def chat_json(self, messages: list[ChatMessage], schema: dict) -> str:
        self.calls.append(messages)
        self.schemas.append(schema)
        if self.error is not None:
            raise self.error
        return self.raw_reply if self.raw_reply is not None else json.dumps(self.reply)

    @property
    def last_prompt(self) -> str:
        return self.calls[-1][-1].content

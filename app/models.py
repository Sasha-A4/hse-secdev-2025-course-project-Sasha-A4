from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class FeatureCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("title")
    @classmethod
    def validate_title_chars(cls, v: str) -> str:
        """Проверка на допустимые символы в заголовке"""
        if not v:
            raise ValueError("title cannot be empty")
        # Запрещаем потенциально опасные символы
        dangerous_chars = ["<", ">", "\x00", "\r", "\n"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"title contains forbidden character: {repr(char)}")
        return v

    @field_validator("title", "description", mode="after")
    @classmethod
    def normalize_whitespace(cls, v: str) -> str:
        """Нормализация: удаление лишних пробелов, табуляций, переносов строк"""
        if not isinstance(v, str):
            return v
        # Удаляем управляющие символы кроме пробелов
        normalized = " ".join(v.split())
        return normalized.strip()


class VoteRequest(BaseModel):
    value: Annotated[int, Field(ge=-1, le=1)]  # +1 or -1


class Feature(BaseModel):
    id: int
    title: str
    description: str
    votes: int

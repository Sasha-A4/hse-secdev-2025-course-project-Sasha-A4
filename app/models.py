from pydantic import BaseModel


class FeatureCreate(BaseModel):
    title: str
    description: str


class VoteRequest(BaseModel):
    value: int  # +1 or -1


class Feature(BaseModel):
    id: int
    title: str
    description: str
    votes: int

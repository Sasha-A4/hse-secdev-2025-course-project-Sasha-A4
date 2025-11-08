from typing import List

from .models import Feature, FeatureCreate, VoteRequest

_FEATURES: List[Feature] = []
_next_feature_id = 1


def get_all_features() -> List[Feature]:
    """Получить список всех фич"""
    return _FEATURES


def create_feature(data: FeatureCreate) -> Feature:
    """Создать новую фичу"""
    global _next_feature_id
    feature = Feature(
        id=_next_feature_id,
        title=data.title,
        description=data.description,
        votes=0,
    )
    _FEATURES.append(feature)
    _next_feature_id += 1
    return feature


def get_top_features(limit: int) -> List[Feature]:
    """Топ фич по голосам"""
    return sorted(_FEATURES, key=lambda f: f.votes, reverse=True)[:limit]


def get_feature_by_id(feature_id: int) -> Feature:
    """Получить одну фичу по ID"""
    for f in _FEATURES:
        if f.id == feature_id:
            return f
    return None


def vote_for_feature(feature_id: int, vote: VoteRequest) -> Feature:
    """Проголосовать за фичу"""
    for f in _FEATURES:
        if f.id == feature_id:
            f.votes += vote.value
            return f
    return None

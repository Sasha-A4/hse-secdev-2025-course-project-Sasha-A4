import time
import uuid
from collections import defaultdict, deque
from typing import List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from . import features
from .models import Feature, FeatureCreate, VoteRequest

app = FastAPI(title="SecDev Course App", version="0.3.0")


# -------- Rate Limiting (NFR-07) --------
_RATE_LIMIT_RPS = 10  # per IP
_RATE_WINDOW_SEC = 1.0
_ip_to_requests = defaultdict(lambda: deque())  # ip -> deque[timestamps]


@app.middleware("http")
async def correlation_and_rate_limit_middleware(request: Request, call_next):
    # Correlation ID setup
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    if request.url.path == "/health":
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _ip_to_requests[client_ip]

    threshold = now - _RATE_WINDOW_SEC
    while window and window[0] < threshold:
        window.popleft()

    if len(window) >= _RATE_LIMIT_RPS:
        problem = _build_problem(
            request,
            status=429,
            title="Too Many Requests",
            detail="Rate limit exceeded",
            type_="https://example.com/problems/rate_limited",
        )
        return JSONResponse(
            status_code=429,
            content=problem,
            headers={
                "Retry-After": "1",
                "Content-Type": "application/problem+json",
                "X-Correlation-ID": correlation_id,
            },
        )

    window.append(now)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# -------- Errors --------
class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


def _build_problem(
    request: Request, status: int, title: str, detail: str, type_: str = "about:blank"
):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "correlation_id": correlation_id,
    }


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    title_map = {
        "validation_error": "Validation Error",
        "not_found": "Not Found",
        "rate_limited": "Too Many Requests",
        "http_error": "HTTP Error",
    }
    problem = _build_problem(
        request,
        status=exc.status,
        title=title_map.get(exc.code, "Bad Request"),
        detail=exc.message,
        type_=f"https://example.com/problems/{exc.code}",
    )
    return JSONResponse(
        status_code=exc.status,
        content=problem,
        headers={
            "Content-Type": "application/problem+json",
            "X-Correlation-ID": problem["correlation_id"],
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    problem = _build_problem(
        request,
        status=exc.status_code,
        title="HTTP Error",
        detail=detail,
        type_="https://example.com/problems/http_error",
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        headers={
            "Content-Type": "application/problem+json",
            "X-Correlation-ID": problem["correlation_id"],
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    problem = _build_problem(
        request,
        status=500,
        title="Internal Server Error",
        detail="An unexpected error occurred",
        type_="https://example.com/problems/internal_error",
    )
    return JSONResponse(
        status_code=500,
        content=problem,
        headers={
            "Content-Type": "application/problem+json",
            "X-Correlation-ID": problem["correlation_id"],
        },
    )


# -------- Health --------
@app.get("/health")
def health():
    return {"status": "ok"}


# -------- Demo Items (для тестов) --------
_DB = {"items": []}


@app.post("/items")
def create_item(name: str):
    if not name or len(name) > 100:
        raise ApiError(code="validation_error", message="name must be 1..100 chars", status=422)
    item = {"id": len(_DB["items"]) + 1, "name": name}
    _DB["items"].append(item)
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for it in _DB["items"]:
        if it["id"] == item_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


# -------- Feature Votes --------


@app.get("/features", response_model=List[Feature])
def list_features():
    """Получить список всех фич"""
    return features.get_all_features()


@app.post("/features", response_model=Feature)
def create_feature(data: FeatureCreate):
    """Создать новую фичу"""
    if not data.title or len(data.title) > 100:
        raise ApiError(code="validation_error", message="title must be 1..100 chars", status=422)
    return features.create_feature(data)


@app.get("/features/top", response_model=List[Feature])
def top_features(limit: int = Query(5, ge=1, le=100)):
    """Топ фич по голосам"""
    return features.get_top_features(limit)


@app.get("/features/{feature_id}", response_model=Feature)
def get_feature(feature_id: int):
    """Получить одну фичу"""
    feature = features.get_feature_by_id(feature_id)
    if feature is None:
        raise ApiError(code="not_found", message="feature not found", status=404)
    return feature


@app.post("/features/{feature_id}/vote", response_model=Feature)
def vote_feature(feature_id: int, vote: VoteRequest):
    """Проголосовать за фичу"""
    if vote.value not in (-1, 1):
        raise ApiError(code="validation_error", message="vote must be +1 or -1", status=422)
    feature = features.vote_for_feature(feature_id, vote)
    if feature is None:
        raise ApiError(code="not_found", message="feature not found", status=404)
    return feature


@app.get("/")
def root():
    return {"message": "FastAPI app is running!"}

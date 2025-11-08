import time
import uuid
from collections import defaultdict, deque
from typing import List

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import features
from .file_upload import generate_safe_filename, save_file, validate_file
from .models import Feature, FeatureCreate, VoteRequest
from .security import safe_log_error, sanitize_error_detail

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
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    # Маскируем детали ошибки перед отправкой клиенту
    safe_detail = sanitize_error_detail(exc.message)
    # Логируем безопасно
    safe_log_error(
        f"API Error: {exc.code}",
        correlation_id,
        exc.message,
    )
    problem = _build_problem(
        request,
        status=exc.status,
        title=title_map.get(exc.code, "Bad Request"),
        detail=safe_detail,
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic в формате RFC 7807"""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    # Формируем сообщение об ошибке из деталей валидации
    errors = exc.errors()
    error_messages = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors]
    detail = "; ".join(error_messages)
    safe_detail = sanitize_error_detail(detail)
    safe_log_error("Validation error", correlation_id, detail)
    problem = _build_problem(
        request,
        status=422,
        title="Validation Error",
        detail=safe_detail,
        type_="https://example.com/problems/validation_error",
    )
    return JSONResponse(
        status_code=422,
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
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    # Логируем исключение безопасно (без стека и чувствительных данных)
    error_msg = str(exc) if exc else "Unknown error"
    safe_log_error("Unhandled exception", correlation_id, error_msg)
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


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Безопасная загрузка файла с проверкой magic bytes, лимитов и UUID именами"""
    # Чтение файла с лимитом размера
    file_content = await file.read()
    if len(file_content) == 0:
        raise ApiError(
            code="validation_error",
            message="File is empty",
            status=422,
        )

    # Валидация файла
    is_valid, error_msg = validate_file(file_content, file.filename or "unknown")
    if not is_valid:
        raise ApiError(
            code="validation_error",
            message=error_msg or "File validation failed",
            status=422,
        )

    try:
        # Генерация безопасного имени
        safe_filename = generate_safe_filename(file.filename or "file")
        # Сохранение файла
        save_file(file_content, safe_filename)

        return {
            "filename": safe_filename,
            "size": len(file_content),
            "message": "File uploaded successfully",
        }
    except ValueError as e:
        raise ApiError(
            code="validation_error",
            message=str(e),
            status=422,
        )


@app.get("/")
def root():
    return {"message": "FastAPI app is running!"}

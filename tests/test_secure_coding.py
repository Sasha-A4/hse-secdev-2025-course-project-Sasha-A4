"""Негативные тесты для контролов безопасного кодирования (P06)."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ===== Тесты валидации и нормализации ввода =====


def test_validation_empty_title():
    """Негативный тест: пустой заголовок"""
    r = client.post("/features", json={"title": "", "description": "Test"})
    assert r.status_code == 422


def test_validation_title_too_long():
    """Негативный тест: заголовок превышает лимит"""
    long_title = "a" * 101
    r = client.post("/features", json={"title": long_title, "description": "Test"})
    assert r.status_code == 422


def test_validation_title_dangerous_chars():
    """Негативный тест: опасные символы в заголовке"""
    dangerous_titles = [
        "<script>alert('xss')</script>",
        "Title\nwith\nnewlines",
        "Title\rwith\rcarriage",
        "Title\x00with\x00null",
    ]
    for title in dangerous_titles:
        r = client.post("/features", json={"title": title, "description": "Test"})
        assert r.status_code == 422, f"Should reject title: {repr(title)}"


def test_validation_description_too_long():
    """Негативный тест: описание превышает лимит"""
    long_desc = "a" * 1001
    r = client.post("/features", json={"title": "Test", "description": long_desc})
    assert r.status_code == 422


def test_validation_normalization_whitespace():
    """Позитивный тест: нормализация пробелов"""
    r = client.post(
        "/features",
        json={"title": "  Test  Title  ", "description": "  Test  Description  "},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Test Title"  # Нормализовано
    assert data["description"] == "Test Description"  # Нормализовано


def test_validation_vote_invalid_range():
    """Негативный тест: голос вне допустимого диапазона"""
    # Создаем фичу
    client.post("/features", json={"title": "Test", "description": "Test"})
    # Пробуем недопустимые значения
    for invalid_vote in [-2, 0, 2, 100, -100]:
        r = client.post("/features/1/vote", json={"value": invalid_vote})
        assert r.status_code == 422, f"Should reject vote: {invalid_vote}"


# ===== Тесты маскирования PII =====


def test_pii_masking_in_error():
    """Тест: PII маскируется в ошибках"""
    from app.security import mask_pii

    # Email
    assert "u***@example.com" in mask_pii("user@example.com")
    # Телефон
    masked = mask_pii("Contact: +7 999 123-45-67")
    assert "***" in masked
    # Кредитная карта
    masked = mask_pii("Card: 1234 5678 9012 3456")
    assert "**** **** **** 3456" in masked


# ===== Тесты безопасной работы с файлами =====


def test_file_upload_empty():
    """Негативный тест: пустой файл"""
    file_content = b""
    r = client.post("/upload", files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")})
    assert r.status_code == 422
    assert "empty" in r.json()["detail"].lower()


def test_file_upload_too_large():
    """Негативный тест: файл превышает лимит размера"""
    # Создаем файл больше 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
    r = client.post(
        "/upload",
        files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")},
    )
    assert r.status_code == 422
    assert "size" in r.json()["detail"].lower() or "limit" in r.json()["detail"].lower()


def test_file_upload_wrong_magic_bytes():
    """Негативный тест: неверные magic bytes"""
    # Файл с расширением .png, но содержимое не PNG
    fake_png = b"FAKE_PNG_CONTENT"
    r = client.post(
        "/upload",
        files={"file": ("fake.png", io.BytesIO(fake_png), "image/png")},
    )
    assert r.status_code == 422
    assert "magic bytes" in r.json()["detail"].lower() or "type" in r.json()["detail"].lower()


def test_file_upload_mismatched_extension():
    """Негативный тест: несоответствие magic bytes и расширения"""
    # PNG файл с расширением .txt
    png_content = b"\x89PNG\r\n\x1a\n" + b"fake png data"
    r = client.post(
        "/upload",
        files={"file": ("image.txt", io.BytesIO(png_content), "text/plain")},
    )
    assert r.status_code == 422
    assert "match" in r.json()["detail"].lower() or "extension" in r.json()["detail"].lower()


def test_file_upload_forbidden_extension():
    """Негативный тест: запрещенное расширение"""
    # Пробуем загрузить .exe файл
    exe_content = b"MZ\x90\x00"  # PE header
    r = client.post(
        "/upload",
        files={"file": ("malware.exe", io.BytesIO(exe_content), "application/x-msdownload")},
    )
    assert r.status_code == 422
    assert "not allowed" in r.json()["detail"].lower() or "extension" in r.json()["detail"].lower()


def test_file_upload_path_traversal():
    """Негативный тест: попытка path traversal через имя файла"""
    # Пробуем использовать ../ в имени файла
    safe_content = b"test content"
    r = client.post(
        "/upload",
        files={"file": ("../../../etc/passwd.txt", io.BytesIO(safe_content), "text/plain")},
    )
    # Должен либо отклонить, либо сохранить с безопасным UUID именем
    # Проверяем, что файл не сохранился в корневой директории
    if r.status_code == 200:
        # Если принят, имя должно быть UUID
        data = r.json()
        assert "filename" in data
        assert "../" not in data["filename"]
        assert data["filename"].startswith("uploads/") or len(data["filename"].split("/")) == 1


def test_file_upload_valid_png():
    """Позитивный тест: валидный PNG файл"""
    # Минимальный валидный PNG
    png_content = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00"
        b"\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = client.post(
        "/upload",
        files={"file": ("test.png", io.BytesIO(png_content), "image/png")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert data["filename"].endswith(".png")
    assert data["size"] == len(png_content)


def test_file_upload_valid_txt():
    """Позитивный тест: валидный текстовый файл"""
    txt_content = b"Hello, World! This is a test file."
    r = client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(txt_content), "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert data["filename"].endswith(".txt")
    assert data["size"] == len(txt_content)

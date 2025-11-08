"""Безопасная работа с файлами: проверка magic bytes, лимиты, UUID имена."""

import uuid
from pathlib import Path
from typing import Optional, Tuple

# Лимиты
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg"}
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Magic bytes для проверки типов файлов
MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",  # JPEG
    b"%PDF": ".pdf",
    b"\x50\x4b\x03\x04": ".zip",  # ZIP (может быть .docx и т.д.)
}


def get_file_mime_type(file_content: bytes) -> Optional[str]:
    """Определяет тип файла по magic bytes"""
    if len(file_content) < 4:
        return None
    for magic, ext in MAGIC_BYTES.items():
        if file_content.startswith(magic):
            return ext
    # Текстовые файлы
    try:
        file_content[:100].decode("utf-8")
        return ".txt"
    except UnicodeDecodeError:
        pass
    return None


def validate_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """Валидация файла: размер, расширение, magic bytes"""
    # Проверка размера
    if len(file_content) > MAX_FILE_SIZE:
        return False, f"File size exceeds limit of {MAX_FILE_SIZE} bytes"

    # Проверка расширения (сначала, чтобы быстро отклонить запрещенные типы)
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension {file_ext} is not allowed"

    # Проверка magic bytes
    detected_type = get_file_mime_type(file_content)
    if detected_type is None:
        return False, "File type could not be determined from magic bytes"

    # Проверка соответствия magic bytes и расширения
    if detected_type != file_ext:
        return False, f"File content type ({detected_type}) does not match extension ({file_ext})"

    return True, None


def generate_safe_filename(original_filename: str) -> str:
    """Генерирует безопасное имя файла с UUID"""
    # Извлекаем расширение
    ext = Path(original_filename).suffix.lower()
    # Генерируем UUID имя
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name


def save_file(file_content: bytes, safe_filename: str) -> Path:
    """Сохраняет файл в безопасную директорию"""
    # Убеждаемся, что имя файла не содержит путь (только имя)
    if "/" in safe_filename or "\\" in safe_filename:
        raise ValueError("Invalid file path: path traversal detected")

    # Канонизация пути
    upload_dir_abs = UPLOAD_DIR.resolve()
    file_path = (upload_dir_abs / safe_filename).resolve()

    # Проверка, что файл находится в UPLOAD_DIR (защита от path traversal)
    try:
        file_path.relative_to(upload_dir_abs)
    except ValueError:
        raise ValueError("Invalid file path: path traversal detected")

    # Проверка на симлинки (если поддерживается ОС)
    if file_path.exists():
        if file_path.is_symlink():
            raise ValueError("Symlink detected: not allowed")

    # Сохранение файла
    file_path.write_bytes(file_content)
    return file_path

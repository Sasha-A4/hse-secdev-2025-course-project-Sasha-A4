# tests/conftest.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_runtest_setup():
    """Очистка rate limiter перед каждым тестом"""
    from app.main import _ip_to_requests

    _ip_to_requests.clear()

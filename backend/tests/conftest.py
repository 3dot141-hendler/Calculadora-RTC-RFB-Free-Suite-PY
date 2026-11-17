"""Fixtures compartilhadas para testes da API FastAPI."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Cliente HTTP de teste síncrono para a aplicação FastAPI."""
    app = create_app()
    return TestClient(app)


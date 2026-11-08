"""Fixtures compartilhadas. Cada teste usa um banco SQLite novo, num arquivo temporário."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'teste.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(session_factory):
    """Uma sessão para testar as regras de negócio diretamente (sem HTTP)."""
    with session_factory() as sessao:
        yield sessao


@pytest.fixture
def client(session_factory):
    """Cliente HTTP de teste; cada requisição abre uma sessão no banco temporário."""

    def _get_db():
        with session_factory() as sessao:
            yield sessao

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

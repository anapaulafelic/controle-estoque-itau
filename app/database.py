"""Conexão com o banco (SQLite) e sessão por requisição."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./estoque.db"

# check_same_thread=False: o FastAPI executa rotas síncronas numa pool de threads,
# e por padrão o SQLite proíbe usar a mesma conexão em outra thread.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# expire_on_commit=False: depois do commit os objetos mantêm os valores em memória,
# sem precisar consultar o banco de novo para montar a resposta.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe base de todos os modelos (tabelas)."""


def get_db():
    """Dependência do FastAPI: abre uma sessão por requisição e sempre a fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Ponto de entrada: cria o app, registra as rotas e traduz erros de negócio em HTTP.

Rodar:  uvicorn app.main:app --reload     (Swagger em http://127.0.0.1:8000/docs)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app import models  # noqa: F401  (importar registra as tabelas em Base.metadata)
from app.database import Base, engine
from app.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ErroDeDominio,
    EstoqueInsuficiente,
    ProdutoIdInvalido,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from app.routes import router

DESCRICAO = """
Controle de estoque com as quantidades **total**, **disponível**, **reservada** e **bloqueada**.

Regra central: `total = disponível + reservada + bloqueada`.

* **Entrada** soma ao total. **Saída** só retira unidades *disponíveis*.
* **Reservar** e **Bloquear** tiram unidades do disponível. Cada reserva e cada bloqueio recebe um `id`
  próprio, pode ser consultado e é liberado de forma independente (**Liberar reserva**, **Liberar bloqueio**).
* **Consultar** mostra a situação atual do produto.
"""

# Qual código HTTP corresponde a cada erro de regra de negócio.
STATUS_HTTP = {
    ProdutoNaoEncontrado: 404,
    ReservaNaoEncontrada: 404,
    BloqueioNaoEncontrado: 404,
    EstoqueInsuficiente: 409,
    ReservaJaLiberada: 409,
    BloqueioJaLiberado: 409,
    QuantidadeInvalida: 422,
    ProdutoIdInvalido: 422,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # cria as tabelas ao iniciar, se ainda não existirem
    yield


app = FastAPI(title="Controle de Estoque", description=DESCRICAO, version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(ErroDeDominio)
async def tratar_erro_de_dominio(request: Request, exc: ErroDeDominio):
    return JSONResponse(status_code=STATUS_HTTP.get(type(exc), 400), content={"detail": str(exc)})


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse(url="/docs")

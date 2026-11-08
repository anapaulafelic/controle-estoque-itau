"""Contratos da API (Pydantic): o que a API recebe e o que devolve.

Servem também para gerar a documentação do Swagger (campos, exemplos e restrições).
"""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from app.models import StatusBloqueio, StatusReserva

# StrictInt: aceita só inteiro de verdade (rejeita "10", 2.5 e true).
Quantidade = Annotated[
    StrictInt,
    Field(gt=0, description="Quantidade de unidades (inteiro maior que zero)", examples=[10]),
]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


# ------------------------------------------------------------------ entradas

class QuantidadeIn(BaseModel):
    quantidade: Quantidade


class ReservaIn(BaseModel):
    quantidade: Quantidade
    solicitacao_id: Texto = Field(description="Solicitação/pedido para o qual as unidades são reservadas", examples=["PED-1001"])


class BloqueioIn(BaseModel):
    quantidade: Quantidade
    solicitacao_id: Texto | None = Field(
        default=None, description="Solicitação associada ao bloqueio (opcional)", examples=["SOL-2001"]
    )


# ------------------------------------------------------------------ saídas
# from_attributes=True permite montar estes modelos direto a partir dos objetos do SQLAlchemy.

class ResumoProduto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    total: int
    disponivel: int
    reservada: int
    bloqueada: int


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    produto_id: str
    solicitacao_id: str
    quantidade: int
    status: StatusReserva
    criada_em: datetime
    liberada_em: datetime | None


class BloqueioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    produto_id: str
    solicitacao_id: str | None
    quantidade: int
    status: StatusBloqueio
    criado_em: datetime
    liberado_em: datetime | None


class ErroOut(BaseModel):
    detail: str

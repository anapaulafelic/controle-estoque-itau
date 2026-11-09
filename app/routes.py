"""Rotas HTTP. Cada rota só converte HTTP <-> chamada ao serviço; nenhuma regra de negócio aqui.

Os nomes (resumos no Swagger e funções) seguem o case: Entrada, Saída, Reservar, Bloquear,
Liberar reserva, Liberar bloqueio e Consultar. As listagens são funcionalidades novas para facilitar a navegação entre os produtos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app import schemas, services
from app.database import get_db

router = APIRouter()

Db = Annotated[Session, Depends(get_db)]
ProdutoId = Annotated[
    str,
    Path(
        pattern=services.PADRAO_PRODUTO_ID,  # mesmo padrão que o serviço exige na Entrada
        description="Identificador (SKU) do produto: letras, números, hífen e sublinhado, sem espaços (até 64). Ex.: SKU-001",
        json_schema_extra={"example": "SKU-001"},  # um único exemplo: o Swagger preenche o campo, sem seletor
    ),
]
ReservaId = Annotated[str, Path(description="Identificador da reserva")]
BloqueioId = Annotated[str, Path(description="Identificador do bloqueio")]

# Respostas de erro documentadas no Swagger.
NAO_ENCONTRADO = {"model": schemas.ErroOut, "description": "Produto, reserva ou bloqueio não encontrado"}
CONFLITO = {"model": schemas.ErroOut, "description": "Operação não permitida (estoque insuficiente ou já liberado)"}


# ------------------------------------------------------------------ Estoque

@router.post(
    "/produtos/{produto_id}/entrada",
    response_model=schemas.ResumoProduto,
    tags=["Estoque"],
    summary="Entrada",
)
def entrada(produto_id: ProdutoId, dados: schemas.QuantidadeIn, db: Db):
    """Soma unidades ao total. Cria o produto se ele ainda não existir."""
    return services.entrada(db, produto_id, dados.quantidade)


@router.post(
    "/produtos/{produto_id}/saida",
    response_model=schemas.ResumoProduto,
    tags=["Estoque"],
    summary="Saída",
    responses={404: NAO_ENCONTRADO, 409: CONFLITO},
)
def saida(produto_id: ProdutoId, dados: schemas.QuantidadeIn, db: Db):
    """Retira unidades do estoque. Só é possível retirar unidades **disponíveis**."""
    return services.saida(db, produto_id, dados.quantidade)


@router.get(
    "/produtos/{produto_id}",
    response_model=schemas.ResumoProduto,
    tags=["Estoque"],
    summary="Consultar produto",
    responses={404: NAO_ENCONTRADO},
)
def consultar_produto(produto_id: ProdutoId, db: Db):
    """Situação atual: total, disponível, reservada e bloqueada."""
    return services.consultar_produto(db, produto_id)


@router.get(
    "/produtos",
    response_model=list[schemas.ResumoProduto],
    tags=["Estoque"],
    summary="Listar produtos",
)
def listar_produtos(
    db: Db,
    limite: Annotated[
        int, Query(ge=1, le=services.LIMITE_MAXIMO_LISTAGEM, description="Quantidade de itens (de 1 a 50)")
    ] = services.LIMITE_MAXIMO_LISTAGEM,
):
    """Lista os primeiros produtos, ordenados por id, com suas quantidades.

    Versão simples, sem paginação completa (evolução prevista).
    """
    return services.listar_produtos(db, limite)


# ------------------------------------------------------------------ Reservas

@router.post(
    "/produtos/{produto_id}/reservas",
    response_model=schemas.ReservaOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Reservas"],
    summary="Reservar",
    responses={404: NAO_ENCONTRADO, 409: CONFLITO},
)
def reservar(produto_id: ProdutoId, dados: schemas.ReservaIn, db: Db):
    """Reserva unidades disponíveis para uma solicitação/pedido. Guarde o `id` devolvido para consultar ou liberar."""
    return services.reservar(db, produto_id, dados.quantidade, dados.solicitacao_id)


@router.get(
    "/reservas/{reserva_id}",
    response_model=schemas.ReservaOut,
    tags=["Reservas"],
    summary="Consultar reserva",
    responses={404: NAO_ENCONTRADO},
)
def consultar_reserva(reserva_id: ReservaId, db: Db):
    return services.consultar_reserva(db, reserva_id)


@router.post(
    "/reservas/{reserva_id}/liberar",
    response_model=schemas.ReservaOut,
    tags=["Reservas"],
    summary="Liberar reserva",
    responses={404: NAO_ENCONTRADO, 409: CONFLITO},
)
def liberar_reserva(reserva_id: ReservaId, db: Db):
    """Libera a reserva; as unidades voltam ao disponível."""
    return services.liberar_reserva(db, reserva_id)


@router.get(
    "/produtos/{produto_id}/reservas",
    response_model=list[schemas.ReservaOut],
    tags=["Reservas"],
    summary="Listar reservas",
    responses={404: NAO_ENCONTRADO},
)
def listar_reservas(
    produto_id: ProdutoId,
    db: Db,
    apenas_ativas: Annotated[bool, Query(description="Se verdadeiro, omite as já liberadas")] = False,
):
    return services.listar_reservas(db, produto_id, apenas_ativas)


# ------------------------------------------------------------------ Bloqueios

@router.post(
    "/produtos/{produto_id}/bloqueios",
    response_model=schemas.BloqueioOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Bloqueios"],
    summary="Bloquear",
    responses={404: NAO_ENCONTRADO, 409: CONFLITO},
)
def bloquear(produto_id: ProdutoId, dados: schemas.BloqueioIn, db: Db):
    """Bloqueia unidades disponíveis, tornando-as indisponíveis. Guarde o `id` devolvido."""
    return services.bloquear(db, produto_id, dados.quantidade, dados.solicitacao_id)


@router.get(
    "/bloqueios/{bloqueio_id}",
    response_model=schemas.BloqueioOut,
    tags=["Bloqueios"],
    summary="Consultar bloqueio",
    responses={404: NAO_ENCONTRADO},
)
def consultar_bloqueio(bloqueio_id: BloqueioId, db: Db):
    return services.consultar_bloqueio(db, bloqueio_id)


@router.post(
    "/bloqueios/{bloqueio_id}/liberar",
    response_model=schemas.BloqueioOut,
    tags=["Bloqueios"],
    summary="Liberar bloqueio",
    responses={404: NAO_ENCONTRADO, 409: CONFLITO},
)
def liberar_bloqueio(bloqueio_id: BloqueioId, db: Db):
    """Libera o bloqueio; as unidades voltam ao disponível."""
    return services.liberar_bloqueio(db, bloqueio_id)


@router.get(
    "/produtos/{produto_id}/bloqueios",
    response_model=list[schemas.BloqueioOut],
    tags=["Bloqueios"],
    summary="Listar bloqueios",
    responses={404: NAO_ENCONTRADO},
)
def listar_bloqueios(
    produto_id: ProdutoId,
    db: Db,
    apenas_ativos: Annotated[bool, Query(description="Se verdadeiro, omite os já liberados")] = False,
):
    return services.listar_bloqueios(db, produto_id, apenas_ativos)

"""Regras de negócio do estoque. Toda a lógica mora aqui; as rotas só chamam estas funções.

Os nomes seguem o vocabulário do case: entrada, saida, reservar, bloquear, liberar, consultar.
Reserva e Bloqueio têm funções próprias (liberar_reserva, liberar_bloqueio) porque cada um terá
passos distintos no futuro. A pequena repetição entre elas é proposital.

Padrão de toda operação que altera o estoque:
    1. validar a entrada
    2. pegar o lock
    3. carregar o produto e checar as regras (se falhar aqui, nada foi alterado)
    4. alterar
    5. commit (ainda dentro do lock)
"""
import re
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    EstoqueInsuficiente,
    ProdutoIdInvalido,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from app.models import (
    Bloqueio,
    Produto,
    Reserva,
    StatusBloqueio,
    StatusReserva,
    agora_utc,
)

# Identificador do produto (SKU): só letras, números, hífen e sublinhado, sem espaços, de 1 a 64 caracteres.
# É uma lista de caracteres PERMITIDOS (allowlist): tudo que não está nela é recusado.
# A proteção principal contra SQL injection é o SQLAlchemy, que sempre envia os valores como parâmetros
# e nunca os concatena no SQL. Esta validação é uma segunda camada de defesa.
PADRAO_PRODUTO_ID = r"^[A-Za-z0-9_-]{1,64}$"

# Teto da listagem de produtos (a paginação completa fica como evolução).
LIMITE_MAXIMO_LISTAGEM = 50

# Concorrência: "ler o disponível e depois alterar" não é atômico. Sem proteção, duas
# requisições simultâneas poderiam ler disponível = 10 e as duas reservarem 8.
# Este lock faz uma operação por vez enxergar o resultado da anterior.
# Limitação: vale para UM processo (um worker do uvicorn). Em produção, a proteção
# ficaria no banco (transação com lock de linha ou versionamento otimista).
_lock = threading.Lock()


def _validar_quantidade(quantidade) -> None:
    # type(...) is not int também rejeita True/False (bool é subclasse de int) e floats.
    if type(quantidade) is not int or quantidade <= 0:
        raise QuantidadeInvalida(quantidade)


def _validar_produto_id(produto_id) -> None:
    # fullmatch exige que a string INTEIRA case com o padrão (inclusive recusa "SKU-1\n").
    if not isinstance(produto_id, str) or not re.fullmatch(PADRAO_PRODUTO_ID, produto_id):
        raise ProdutoIdInvalido()


def _buscar_produto(db: Session, produto_id: str) -> Produto:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise ProdutoNaoEncontrado(produto_id)
    return produto


def _exigir_disponivel(produto: Produto, quantidade: int) -> None:
    if quantidade > produto.disponivel:
        raise EstoqueInsuficiente(produto.id, quantidade, produto.disponivel)


# ---------------------------------------------------------------- Entrada e Saída

def entrada(db: Session, produto_id: str, quantidade: int) -> Produto:
    """Soma ao total. Se o produto não existe, ele é criado (não há função de cadastro).
    Como é o único ponto que cria produtos, é aqui que o formato do id é exigido."""
    _validar_quantidade(quantidade)
    _validar_produto_id(produto_id)
    with _lock:
        produto = db.get(Produto, produto_id)
        if produto is None:
            produto = Produto(id=produto_id, total=0)
            db.add(produto)
        produto.total += quantidade
        db.commit()
        return produto


def saida(db: Session, produto_id: str, quantidade: int) -> Produto:
    """Retira do total, mas só unidades DISPONÍVEIS (nunca as reservadas ou bloqueadas)."""
    _validar_quantidade(quantidade)
    with _lock:
        produto = _buscar_produto(db, produto_id)
        _exigir_disponivel(produto, quantidade)
        produto.total -= quantidade
        db.commit()
        return produto


# ---------------------------------------------------------------- Reservar e Liberar reserva

def reservar(db: Session, produto_id: str, quantidade: int, solicitacao_id: str) -> Reserva:
    """Reserva unidades disponíveis para uma solicitação/pedido e devolve a reserva (com o id)."""
    _validar_quantidade(quantidade)
    with _lock:
        produto = _buscar_produto(db, produto_id)
        _exigir_disponivel(produto, quantidade)
        reserva = Reserva(quantidade=quantidade, solicitacao_id=solicitacao_id)
        produto.reservas.append(reserva)
        db.commit()
        db.refresh(reserva)  # devolve o registro exatamente como foi gravado (id, datas)
        return reserva


def liberar_reserva(db: Session, reserva_id: str) -> Reserva:
    """Libera a reserva. As unidades voltam ao disponível automaticamente, porque o disponível
    é calculado só com as reservas ATIVAS."""
    with _lock:
        reserva = db.get(Reserva, reserva_id)
        if reserva is None:
            raise ReservaNaoEncontrada(reserva_id)
        if reserva.status == StatusReserva.LIBERADA:
            raise ReservaJaLiberada(reserva_id)
        reserva.status = StatusReserva.LIBERADA
        reserva.liberada_em = agora_utc()
        db.commit()
        return reserva


# ---------------------------------------------------------------- Bloquear e Liberar bloqueio

def bloquear(db: Session, produto_id: str, quantidade: int, solicitacao_id: str | None = None) -> Bloqueio:
    """Bloqueia unidades disponíveis, tornando-as indisponíveis, e devolve o bloqueio (com o id)."""
    _validar_quantidade(quantidade)
    with _lock:
        produto = _buscar_produto(db, produto_id)
        _exigir_disponivel(produto, quantidade)
        bloqueio = Bloqueio(quantidade=quantidade, solicitacao_id=solicitacao_id)
        produto.bloqueios.append(bloqueio)
        db.commit()
        db.refresh(bloqueio)
        return bloqueio


def liberar_bloqueio(db: Session, bloqueio_id: str) -> Bloqueio:
    """Libera o bloqueio. As unidades voltam ao disponível automaticamente."""
    with _lock:
        bloqueio = db.get(Bloqueio, bloqueio_id)
        if bloqueio is None:
            raise BloqueioNaoEncontrado(bloqueio_id)
        if bloqueio.status == StatusBloqueio.LIBERADO:
            raise BloqueioJaLiberado(bloqueio_id)
        bloqueio.status = StatusBloqueio.LIBERADO
        bloqueio.liberado_em = agora_utc()
        db.commit()
        return bloqueio


# ---------------------------------------------------------------- Consultar

def consultar_produto(db: Session, produto_id: str) -> Produto:
    """Situação do produto. Usa o lock para ler o total, as reservas e os bloqueios do mesmo
    instante, senão uma escrita no meio poderia produzir um resumo que nunca existiu."""
    with _lock:
        return _buscar_produto(db, produto_id)


def consultar_reserva(db: Session, reserva_id: str) -> Reserva:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise ReservaNaoEncontrada(reserva_id)
    return reserva


def consultar_bloqueio(db: Session, bloqueio_id: str) -> Bloqueio:
    bloqueio = db.get(Bloqueio, bloqueio_id)
    if bloqueio is None:
        raise BloqueioNaoEncontrado(bloqueio_id)
    return bloqueio


# ---------------------------------------------------------------- Listagens (funcionalidades novas)

def listar_produtos(db: Session, limite: int = LIMITE_MAXIMO_LISTAGEM) -> list[Produto]:
    """Os primeiros produtos, ordenados por id, no máximo `limite` (de 1 a 50).
    Versão simples: a paginação completa fica como evolução."""
    if not 1 <= limite <= LIMITE_MAXIMO_LISTAGEM:
        raise ValueError(f"limite deve estar entre 1 e {LIMITE_MAXIMO_LISTAGEM}")
    with _lock:  # mesmo motivo do consultar_produto: valores lidos do mesmo instante
        return list(db.scalars(select(Produto).order_by(Produto.id).limit(limite)))


def listar_reservas(db: Session, produto_id: str, apenas_ativas: bool = False) -> list[Reserva]:
    produto = _buscar_produto(db, produto_id)
    return [r for r in produto.reservas if not apenas_ativas or r.status == StatusReserva.ATIVA]


def listar_bloqueios(db: Session, produto_id: str, apenas_ativos: bool = False) -> list[Bloqueio]:
    produto = _buscar_produto(db, produto_id)
    return [b for b in produto.bloqueios if not apenas_ativos or b.status == StatusBloqueio.ATIVO]

"""Tabelas do banco (SQLAlchemy) e o modelo de domínio.

Linguagem do case: Produto, Reserva, Bloqueio.

- Produto é a raiz do agregado: dono do total e das suas reservas e bloqueios.
- Reserva e Bloqueio são entidades distintas, cada uma com o seu status e o seu ciclo de vida.
  (Por exemplo, a reserva poderá ganhar o passo "efetivada" no futuro; o bloqueio não.)
- O produto guarda só o TOTAL. As quantidades reservada, bloqueada e disponível são CALCULADAS a
  partir das reservas e bloqueios ativos. Assim a regra  total = disponível + reservada + bloqueada
  nunca diverge: existe uma única fonte de verdade.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def agora_utc() -> datetime:
    """Data/hora atual em UTC, sem fuso (o SQLite não guarda fuso horário)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class StatusReserva(str, Enum):
    ATIVA = "ATIVA"
    LIBERADA = "LIBERADA"
    # Evolução prevista: EFETIVADA (as unidades da reserva saem do estoque, mas mantém o registro para rastreabilidade).


class StatusBloqueio(str, Enum):
    ATIVO = "ATIVO"
    LIBERADO = "LIBERADO"


class Produto(Base):
    __tablename__ = "produtos"
    # Última linha de defesa: mesmo que um bug passe pelas regras, o banco recusa total negativo.
    __table_args__ = (CheckConstraint("total >= 0", name="ck_produtos_total_nao_negativo"),)

    id: Mapped[str] = mapped_column(primary_key=True)  # identificação do produto (SKU)
    total: Mapped[int] = mapped_column(default=0)

    # lazy="selectin": ao carregar o produto, as reservas e os bloqueios vêm junto (consultas extras).
    # Assim os cálculos abaixo nunca disparam consultas escondidas fora do lock ou da sessão.
    reservas: Mapped[list["Reserva"]] = relationship(
        back_populates="produto", lazy="selectin", order_by="Reserva.criada_em"
    )
    bloqueios: Mapped[list["Bloqueio"]] = relationship(
        back_populates="produto", lazy="selectin", order_by="Bloqueio.criado_em"
    )

    @property
    def reservada(self) -> int:
        return sum(r.quantidade for r in self.reservas if r.status == StatusReserva.ATIVA)

    @property
    def bloqueada(self) -> int:
        return sum(b.quantidade for b in self.bloqueios if b.status == StatusBloqueio.ATIVO)

    @property
    def disponivel(self) -> int:
        return self.total - self.reservada - self.bloqueada


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (CheckConstraint("quantidade > 0", name="ck_reservas_quantidade_positiva"),)

    # A identificação é gerada pelo sistema e devolvida ao cliente, que a usa para consultar e liberar.
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    produto_id: Mapped[str] = mapped_column(ForeignKey("produtos.id"), index=True)
    solicitacao_id: Mapped[str]  # solicitação/pedido para o qual as unidades foram reservadas
    quantidade: Mapped[int]
    status: Mapped[StatusReserva] = mapped_column(SAEnum(StatusReserva), default=StatusReserva.ATIVA)
    criada_em: Mapped[datetime] = mapped_column(default=agora_utc)
    liberada_em: Mapped[datetime | None]

    produto: Mapped["Produto"] = relationship(back_populates="reservas")


class Bloqueio(Base):
    __tablename__ = "bloqueios"
    __table_args__ = (CheckConstraint("quantidade > 0", name="ck_bloqueios_quantidade_positiva"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    produto_id: Mapped[str] = mapped_column(ForeignKey("produtos.id"), index=True)
    solicitacao_id: Mapped[str | None]  # opcional: o case não exige solicitação para bloquear
    quantidade: Mapped[int]
    status: Mapped[StatusBloqueio] = mapped_column(SAEnum(StatusBloqueio), default=StatusBloqueio.ATIVO)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)
    liberado_em: Mapped[datetime | None]

    produto: Mapped["Produto"] = relationship(back_populates="bloqueios")

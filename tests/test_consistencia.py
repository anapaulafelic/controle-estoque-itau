"""Consistência: depois de um pedido recusado, o estoque continua exatamente como estava."""
import pytest

from app import services
from app.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    EstoqueInsuficiente,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)

SKU = "SKU-001"


def conferir(produto, total, disponivel, reservada, bloqueada):
    assert (produto.total, produto.disponivel, produto.reservada, produto.bloqueada) == (
        total,
        disponivel,
        reservada,
        bloqueada,
    )
    assert produto.disponivel >= 0


def estado(db):
    """Fotografia do estoque: as quatro quantidades e quantas reservas e bloqueios existem."""
    p = services.consultar_produto(db, SKU)
    return (
        p.total,
        p.disponivel,
        p.reservada,
        p.bloqueada,
        len(services.listar_reservas(db, SKU)),
        len(services.listar_bloqueios(db, SKU)),
    )


def preparar(db):
    """10 em estoque, 3 reservadas e 2 bloqueadas: sobram 5 disponíveis."""
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 3, "PED-1")
    bloqueio = services.bloquear(db, SKU, 2)
    return reserva, bloqueio


def chamar(db, operacao, quantidade):
    """Chama a operação pelo nome, para o mesmo teste valer para várias operações."""
    if operacao == "reservar":
        return services.reservar(db, SKU, quantidade, "PED-X")
    return getattr(services, operacao)(db, SKU, quantidade)


# ------------------------------------------------------------------ pedidos recusados não alteram o estoque

@pytest.mark.parametrize("quantidade", [0, -1, True])
@pytest.mark.parametrize("operacao", ["entrada", "saida", "reservar", "bloquear"])
def test_quantidade_invalida_em_qualquer_operacao_nao_altera_o_estoque(db, operacao, quantidade):
    """A validação vale em TODAS as operações. Sem ela, saida(-1) aumentaria o estoque."""
    preparar(db)
    antes = estado(db)
    with pytest.raises(QuantidadeInvalida):
        chamar(db, operacao, quantidade)
    assert estado(db) == antes


@pytest.mark.parametrize("operacao", ["saida", "reservar", "bloquear"])
def test_pedido_acima_do_disponivel_nao_altera_o_estoque(db, operacao):
    """Pedir uma unidade a mais do que o disponível (5) é recusado sem mudar nada."""
    preparar(db)
    antes = estado(db)
    with pytest.raises(EstoqueInsuficiente):
        chamar(db, operacao, 6)
    assert estado(db) == antes


def test_liberar_reserva_duas_vezes_nao_altera_o_estoque_nem_a_data_da_primeira(db):
    reserva, _ = preparar(db)
    services.liberar_reserva(db, reserva.id)
    data = services.consultar_reserva(db, reserva.id).liberada_em
    antes = estado(db)
    with pytest.raises(ReservaJaLiberada):
        services.liberar_reserva(db, reserva.id)
    assert estado(db) == antes
    assert services.consultar_reserva(db, reserva.id).liberada_em == data


def test_liberar_bloqueio_duas_vezes_nao_altera_o_estoque_nem_a_data_da_primeira(db):
    _, bloqueio = preparar(db)
    services.liberar_bloqueio(db, bloqueio.id)
    data = services.consultar_bloqueio(db, bloqueio.id).liberado_em
    antes = estado(db)
    with pytest.raises(BloqueioJaLiberado):
        services.liberar_bloqueio(db, bloqueio.id)
    assert estado(db) == antes
    assert services.consultar_bloqueio(db, bloqueio.id).liberado_em == data


def test_apos_varios_erros_seguidos_a_proxima_operacao_valida_funciona(db):
    """Depois de erros de tipos diferentes nada ficou pela metade: o estoque é o mesmo e a sessão segue utilizável."""
    reserva, _ = preparar(db)
    antes = estado(db)
    erros = [
        (lambda: services.reservar(db, SKU, 6, "PED-2"), EstoqueInsuficiente),
        (lambda: services.saida(db, SKU, -1), QuantidadeInvalida),
        (lambda: services.bloquear(db, "NAO-EXISTE", 1), ProdutoNaoEncontrado),
        (lambda: services.liberar_reserva(db, "nao-existe"), ReservaNaoEncontrada),
        (lambda: services.liberar_bloqueio(db, reserva.id), BloqueioNaoEncontrado),
    ]
    for chamada, erro in erros:
        with pytest.raises(erro):
            chamada()
    assert estado(db) == antes

    services.reservar(db, SKU, 5, "PED-2")
    conferir(services.consultar_produto(db, SKU), 10, 0, 8, 2)


# ------------------------------------------------------------------ várias reservas e bloqueios

def test_varias_reservas_e_bloqueios_liberados_fora_de_ordem(db):
    """Cada liberação devolve só a quantidade da PRÓPRIA reserva ou bloqueio, em qualquer ordem."""
    services.entrada(db, SKU, 100)
    r1 = services.reservar(db, SKU, 10, "PED-1")
    r2 = services.reservar(db, SKU, 20, "PED-2")
    r3 = services.reservar(db, SKU, 30, "PED-3")
    b1 = services.bloquear(db, SKU, 5)
    b2 = services.bloquear(db, SKU, 15, "SOL-1")
    conferir(services.consultar_produto(db, SKU), 100, 20, 60, 20)

    passos = [  # (o que liberar, estado depois: total, disponível, reservada, bloqueada)
        (lambda: services.liberar_reserva(db, r2.id), (100, 40, 40, 20)),
        (lambda: services.liberar_bloqueio(db, b1.id), (100, 45, 40, 15)),
        (lambda: services.liberar_reserva(db, r1.id), (100, 55, 30, 15)),
        (lambda: services.liberar_reserva(db, r3.id), (100, 85, 0, 15)),
        (lambda: services.liberar_bloqueio(db, b2.id), (100, 100, 0, 0)),
    ]
    for liberar, esperado in passos:
        liberar()
        conferir(services.consultar_produto(db, SKU), *esperado)


def test_unidades_liberadas_podem_ser_reservadas_e_bloqueadas_de_novo(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 10, "PED-1")
    with pytest.raises(EstoqueInsuficiente):
        services.bloquear(db, SKU, 1)  # tudo está reservado

    services.liberar_reserva(db, reserva.id)
    services.bloquear(db, SKU, 4)
    services.reservar(db, SKU, 6, "PED-2")
    conferir(services.consultar_produto(db, SKU), 10, 0, 6, 4)


def test_produtos_sao_independentes_entre_si(db):
    """Nada vaza de um produto para outro: saldos, listagens e liberações."""
    services.entrada(db, "SKU-A", 10)
    services.entrada(db, "SKU-B", 20)
    reserva_a = services.reservar(db, "SKU-A", 4, "PED-1")
    bloqueio_b = services.bloquear(db, "SKU-B", 5)
    conferir(services.consultar_produto(db, "SKU-A"), 10, 6, 4, 0)
    conferir(services.consultar_produto(db, "SKU-B"), 20, 15, 0, 5)

    assert [r.id for r in services.listar_reservas(db, "SKU-A")] == [reserva_a.id]
    assert services.listar_reservas(db, "SKU-B") == []
    assert services.listar_bloqueios(db, "SKU-A") == []
    assert [b.id for b in services.listar_bloqueios(db, "SKU-B")] == [bloqueio_b.id]

    services.saida(db, "SKU-B", 15)
    services.liberar_reserva(db, reserva_a.id)
    conferir(services.consultar_produto(db, "SKU-A"), 10, 10, 0, 0)
    conferir(services.consultar_produto(db, "SKU-B"), 5, 0, 0, 5)

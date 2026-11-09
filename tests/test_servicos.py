"""Testes das regras de negócio (chamam services.py direto, sem HTTP)."""

import pytest

from app import services
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
from app.models import StatusBloqueio, StatusReserva

SKU = "SKU-001"


def conferir(produto, total, disponivel, reservada, bloqueada):
    """Confere as quatro quantidades; o disponível nunca pode ser negativo."""
    assert (produto.total, produto.disponivel, produto.reservada, produto.bloqueada) == (
        total,
        disponivel,
        reservada,
        bloqueada,
    )
    assert produto.disponivel >= 0


# ------------------------------------------------------------------ Entrada e Saída

def test_entrada_cria_o_produto_e_acumula(db):
    conferir(services.entrada(db, SKU, 10), 10, 10, 0, 0)
    conferir(services.entrada(db, SKU, 5), 15, 15, 0, 0)


def test_saida_reduz_o_total(db):
    services.entrada(db, SKU, 10)
    conferir(services.saida(db, SKU, 4), 6, 6, 0, 0)


def test_saida_pode_retirar_exatamente_o_disponivel(db):
    services.entrada(db, SKU, 10)
    conferir(services.saida(db, SKU, 10), 0, 0, 0, 0)


def test_saida_acima_do_disponivel_falha_sem_alterar_o_estoque(db):
    services.entrada(db, SKU, 10)
    with pytest.raises(EstoqueInsuficiente):
        services.saida(db, SKU, 11)
    conferir(services.consultar_produto(db, SKU), 10, 10, 0, 0)


def test_saida_nao_consome_unidades_reservadas_nem_bloqueadas(db):
    services.entrada(db, SKU, 10)
    services.reservar(db, SKU, 4, "PED-1")
    services.bloquear(db, SKU, 3)  # sobram 3 disponíveis
    with pytest.raises(EstoqueInsuficiente):
        services.saida(db, SKU, 4)
    conferir(services.saida(db, SKU, 3), 7, 0, 4, 3)


# ------------------------------------------------------------------ Reservar e Bloquear

def test_reservar_move_unidades_do_disponivel_para_reservada(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 4, "PED-1")
    assert reserva.id
    assert reserva.status == StatusReserva.ATIVA
    assert reserva.quantidade == 4
    assert reserva.solicitacao_id == "PED-1"
    conferir(services.consultar_produto(db, SKU), 10, 6, 4, 0)


def test_bloquear_move_unidades_do_disponivel_para_bloqueada(db):
    services.entrada(db, SKU, 10)
    bloqueio = services.bloquear(db, SKU, 3)  # solicitação é opcional no bloqueio
    assert bloqueio.id
    assert bloqueio.status == StatusBloqueio.ATIVO
    assert bloqueio.solicitacao_id is None
    conferir(services.consultar_produto(db, SKU), 10, 7, 0, 3)


def test_varias_reservas_e_bloqueios_tem_ids_proprios(db):
    services.entrada(db, SKU, 100)
    r1 = services.reservar(db, SKU, 10, "PED-1")
    r2 = services.reservar(db, SKU, 20, "PED-1")  # mesma solicitação: continua sendo outra reserva
    r3 = services.reservar(db, SKU, 5, "PED-2")
    b1 = services.bloquear(db, SKU, 7, "SOL-9")
    assert len({r1.id, r2.id, r3.id, b1.id}) == 4
    conferir(services.consultar_produto(db, SKU), 100, 58, 35, 7)


def test_reservar_e_bloquear_acima_do_disponivel_falham_sem_alterar_o_estoque(db):
    services.entrada(db, SKU, 10)
    services.reservar(db, SKU, 6, "PED-1")  # sobram 4
    with pytest.raises(EstoqueInsuficiente):
        services.reservar(db, SKU, 5, "PED-2")
    with pytest.raises(EstoqueInsuficiente):
        services.bloquear(db, SKU, 5)
    conferir(services.consultar_produto(db, SKU), 10, 4, 6, 0)
    assert len(services.listar_reservas(db, SKU)) == 1
    assert len(services.listar_bloqueios(db, SKU)) == 0


def test_pode_reservar_exatamente_o_disponivel(db):
    services.entrada(db, SKU, 10)
    services.reservar(db, SKU, 10, "PED-1")
    conferir(services.consultar_produto(db, SKU), 10, 0, 10, 0)


# ------------------------------------------------------------------ Liberar reserva e Liberar bloqueio

def test_liberar_reserva_devolve_a_quantidade_ao_disponivel(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 4, "PED-1")
    liberada = services.liberar_reserva(db, reserva.id)
    assert liberada.status == StatusReserva.LIBERADA
    assert liberada.liberada_em is not None
    conferir(services.consultar_produto(db, SKU), 10, 10, 0, 0)


def test_liberar_bloqueio_devolve_a_quantidade_ao_disponivel(db):
    services.entrada(db, SKU, 10)
    bloqueio = services.bloquear(db, SKU, 3)
    liberado = services.liberar_bloqueio(db, bloqueio.id)
    assert liberado.status == StatusBloqueio.LIBERADO
    assert liberado.liberado_em is not None
    conferir(services.consultar_produto(db, SKU), 10, 10, 0, 0)


def test_liberacao_e_independente_entre_reservas(db):
    services.entrada(db, SKU, 10)
    r1 = services.reservar(db, SKU, 3, "PED-1")
    r2 = services.reservar(db, SKU, 4, "PED-2")
    services.liberar_reserva(db, r1.id)
    conferir(services.consultar_produto(db, SKU), 10, 6, 4, 0)
    assert services.consultar_reserva(db, r2.id).status == StatusReserva.ATIVA


def test_liberar_reserva_nao_afeta_os_bloqueios(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 3, "PED-1")
    bloqueio = services.bloquear(db, SKU, 2)
    services.liberar_reserva(db, reserva.id)
    conferir(services.consultar_produto(db, SKU), 10, 8, 0, 2)
    assert services.consultar_bloqueio(db, bloqueio.id).status == StatusBloqueio.ATIVO


def test_liberar_reserva_duas_vezes_falha_e_nao_devolve_a_quantidade_em_dobro(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 4, "PED-1")
    services.liberar_reserva(db, reserva.id)
    with pytest.raises(ReservaJaLiberada):
        services.liberar_reserva(db, reserva.id)
    conferir(services.consultar_produto(db, SKU), 10, 10, 0, 0)


def test_liberar_bloqueio_duas_vezes_falha_e_nao_devolve_a_quantidade_em_dobro(db):
    services.entrada(db, SKU, 10)
    bloqueio = services.bloquear(db, SKU, 4)
    services.liberar_bloqueio(db, bloqueio.id)
    with pytest.raises(BloqueioJaLiberado):
        services.liberar_bloqueio(db, bloqueio.id)
    conferir(services.consultar_produto(db, SKU), 10, 10, 0, 0)


def test_liberar_reserva_ou_bloqueio_inexistente(db):
    with pytest.raises(ReservaNaoEncontrada):
        services.liberar_reserva(db, "nao-existe")
    with pytest.raises(BloqueioNaoEncontrado):
        services.liberar_bloqueio(db, "nao-existe")


def test_reserva_e_bloqueio_nao_se_liberam_pelo_id_um_do_outro(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 2, "PED-1")
    bloqueio = services.bloquear(db, SKU, 3)
    with pytest.raises(BloqueioNaoEncontrado):
        services.liberar_bloqueio(db, reserva.id)
    with pytest.raises(ReservaNaoEncontrada):
        services.liberar_reserva(db, bloqueio.id)
    conferir(services.consultar_produto(db, SKU), 10, 5, 2, 3)


def test_cenario_completo_do_exemplo(db):
    services.entrada(db, SKU, 100)
    reserva = services.reservar(db, SKU, 30, "PED-1")
    services.bloquear(db, SKU, 10)
    conferir(services.saida(db, SKU, 60), 40, 0, 30, 10)
    services.liberar_reserva(db, reserva.id)
    conferir(services.consultar_produto(db, SKU), 40, 30, 0, 10)


# ------------------------------------------------------------------ validações e erros

@pytest.mark.parametrize("quantidade", [0, -1, True, 2.5, "3", services.QUANTIDADE_MAXIMA + 1, 2**63])
def test_quantidade_invalida_e_rejeitada(db, quantidade):
    with pytest.raises(QuantidadeInvalida):
        services.entrada(db, SKU, quantidade)


def test_operacoes_em_produto_inexistente(db):
    with pytest.raises(ProdutoNaoEncontrado):
        services.saida(db, "NAO-EXISTE", 1)
    with pytest.raises(ProdutoNaoEncontrado):
        services.reservar(db, "NAO-EXISTE", 1, "PED-1")
    with pytest.raises(ProdutoNaoEncontrado):
        services.bloquear(db, "NAO-EXISTE", 1)
    with pytest.raises(ProdutoNaoEncontrado):
        services.consultar_produto(db, "NAO-EXISTE")
    with pytest.raises(ProdutoNaoEncontrado):
        services.listar_reservas(db, "NAO-EXISTE")
    with pytest.raises(ProdutoNaoEncontrado):
        services.listar_bloqueios(db, "NAO-EXISTE")


# ------------------------------------------------------------------ Consultar e listar

def test_consultar_reserva_e_bloqueio_por_id(db):
    services.entrada(db, SKU, 10)
    reserva = services.reservar(db, SKU, 4, "PED-1")
    bloqueio = services.bloquear(db, SKU, 2)
    assert services.consultar_reserva(db, reserva.id).id == reserva.id
    assert services.consultar_bloqueio(db, bloqueio.id).id == bloqueio.id
    with pytest.raises(ReservaNaoEncontrada):
        services.consultar_reserva(db, "nao-existe")
    with pytest.raises(BloqueioNaoEncontrado):
        services.consultar_bloqueio(db, "nao-existe")


def test_listar_reservas_com_filtro_de_ativas(db):
    services.entrada(db, SKU, 10)
    r1 = services.reservar(db, SKU, 3, "PED-1")
    r2 = services.reservar(db, SKU, 2, "PED-2")
    services.liberar_reserva(db, r1.id)
    assert len(services.listar_reservas(db, SKU)) == 2
    assert [r.id for r in services.listar_reservas(db, SKU, apenas_ativas=True)] == [r2.id]


def test_listar_bloqueios_com_filtro_de_ativos(db):
    services.entrada(db, SKU, 10)
    b1 = services.bloquear(db, SKU, 3)
    b2 = services.bloquear(db, SKU, 2)
    services.liberar_bloqueio(db, b1.id)
    assert len(services.listar_bloqueios(db, SKU)) == 2
    assert [b.id for b in services.listar_bloqueios(db, SKU, apenas_ativos=True)] == [b2.id]


def test_listar_produtos_ordenado_por_id_e_respeita_o_limite(db):
    for sku in ["SKU-C", "SKU-A", "SKU-B"]:
        services.entrada(db, sku, 1)
    assert [p.id for p in services.listar_produtos(db)] == ["SKU-A", "SKU-B", "SKU-C"]
    assert [p.id for p in services.listar_produtos(db, limite=2)] == ["SKU-A", "SKU-B"]


def test_listar_produtos_traz_as_quantidades(db):
    services.entrada(db, SKU, 10)
    services.reservar(db, SKU, 4, "PED-1")
    services.bloquear(db, SKU, 1)
    conferir(services.listar_produtos(db)[0], 10, 5, 4, 1)


def test_listar_produtos_sem_dados_e_limite_invalido(db):
    assert services.listar_produtos(db) == []
    for limite in [0, -1, 51]:
        with pytest.raises(ValueError):
            services.listar_produtos(db, limite=limite)


# ------------------------------------------------------------------ identificador do produto

@pytest.mark.parametrize(
    "produto_id",
    [
        "teste teste",  # espaço no meio
        " SKU-1",
        "SKU-1 ",
        "SKU-1\n",  # quebra de linha no final
        "SKU.1",
        "SKU/1",
        "SKÚ-1",  # acento
        "<script>",
        "x';DROP--",
        "x'; DROP TABLE produtos;--",
        "a" * 65,  # maior que 64
        "",
    ],
)
def test_entrada_rejeita_id_de_produto_invalido_e_nao_cria_o_produto(db, produto_id):
    with pytest.raises(ProdutoIdInvalido):
        services.entrada(db, produto_id, 1)
    assert services.listar_produtos(db) == []


@pytest.mark.parametrize("produto_id", ["SKU-001", "sku_001", "ABC123", "a" * 64])
def test_entrada_aceita_id_de_produto_valido(db, produto_id):
    assert services.entrada(db, produto_id, 1).id == produto_id


def test_listar_produtos_nos_valores_limite_1_e_50(db):
    """Objetivo: valor-limite do parâmetro. 1 e 50 são aceitos (os extremos válidos); 0 e 51 já eram recusados."""
    for sku in ["SKU-A", "SKU-B", "SKU-C"]:
        services.entrada(db, sku, 1)
    assert [p.id for p in services.listar_produtos(db, limite=1)] == ["SKU-A"]
    assert len(services.listar_produtos(db, limite=50)) == 3


def test_quantidade_no_limite_maximo_e_aceita(db):
    """Valor-limite: exatamente a quantidade máxima por operação é aceita."""
    assert services.entrada(db, SKU, services.QUANTIDADE_MAXIMA).total == services.QUANTIDADE_MAXIMA

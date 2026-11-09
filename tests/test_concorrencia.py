"""Concorrência: várias threads reservando ao mesmo tempo."""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import services
from app.exceptions import EstoqueInsuficiente

SKU = "SKU-001"


@pytest.fixture
def conferencia_lenta(monkeypatch):
    """Faz uma pausa de 10 ms logo depois de conferir que há estoque, antes de gravar.

    Sem a pausa, a corrida é tão rápida que o teste passaria até sem o lock. Com a pausa, várias threads
    passariam na conferência antes de qualquer gravação, e o estoque seria ultrapassado. Por isso o teste
    falha de verdade se o lock for removido.
    """
    original = services._exigir_disponivel

    def lenta(produto, quantidade):
        original(produto, quantidade)
        time.sleep(0.01)

    monkeypatch.setattr(services, "_exigir_disponivel", lenta)


def test_reservas_simultaneas_nao_ultrapassam_o_estoque(session_factory, conferencia_lenta):
    """50 tentativas de reservar 1 unidade para 30 em estoque: exatamente 30 passam."""
    with session_factory() as db:
        services.entrada(db, SKU, 30)

    def tentar_reservar(i):
        with session_factory() as sessao:  # cada thread usa a sua própria sessão
            try:
                services.reservar(sessao, SKU, 1, f"PED-{i}")
                return True
            except EstoqueInsuficiente:
                return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        resultados = list(pool.map(tentar_reservar, range(50)))

    assert sum(resultados) == 30
    with session_factory() as nova:  # sessão nova: lê o que foi gravado no banco
        produto = services.consultar_produto(nova, SKU)
        assert (produto.total, produto.disponivel, produto.reservada) == (30, 0, 30)

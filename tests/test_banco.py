"""Banco de dados dos testes: cada teste usa um banco próprio e nunca toca o estoque.db real."""
import pytest

from app import services
from app.database import engine as engine_do_projeto

SKU = "SKU-001"


def test_o_banco_dos_testes_nao_e_o_do_projeto(db):
    assert str(db.get_bind().url) != str(engine_do_projeto.url)


@pytest.mark.parametrize("repeticao", [1, 2, 3])
def test_cada_teste_comeca_com_o_banco_vazio(db, repeticao):
    """O mesmo teste repetido 3 vezes parte sempre do zero. Se o banco fosse compartilhado,
    a segunda repetição enxergaria o produto da primeira e o total deixaria de ser 10."""
    assert services.listar_produtos(db) == []
    assert services.entrada(db, SKU, 10).total == 10


def test_a_api_grava_no_banco_isolado(client, session_factory):
    """As requisições HTTP do teste caem no banco temporário (a dependência get_db foi trocada)."""
    client.post(f"/produtos/{SKU}/entrada", json={"quantidade": 7})
    with session_factory() as sessao:
        assert [(p.id, p.total) for p in services.listar_produtos(sessao)] == [(SKU, 7)]

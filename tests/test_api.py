"""Testes da API (HTTP): rotas, códigos de status e formato das respostas."""
import pytest


def test_fluxo_completo_pela_api(client):
    resposta = client.post("/produtos/SKU-001/entrada", json={"quantidade": 100})
    assert resposta.status_code == 200
    assert resposta.json() == {"id": "SKU-001", "total": 100, "disponivel": 100, "reservada": 0, "bloqueada": 0}

    reserva = client.post("/produtos/SKU-001/reservas", json={"quantidade": 30, "solicitacao_id": "PED-1"})
    assert reserva.status_code == 201
    assert reserva.json()["status"] == "ATIVA"
    assert reserva.json()["solicitacao_id"] == "PED-1"
    reserva_id = reserva.json()["id"]

    bloqueio = client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 10, "solicitacao_id": "SOL-7"})
    assert bloqueio.status_code == 201
    assert bloqueio.json()["status"] == "ATIVO"
    bloqueio_id = bloqueio.json()["id"]

    resumo = client.get("/produtos/SKU-001")
    assert resumo.json() == {"id": "SKU-001", "total": 100, "disponivel": 60, "reservada": 30, "bloqueada": 10}

    saida = client.post("/produtos/SKU-001/saida", json={"quantidade": 60})
    assert saida.status_code == 200
    assert saida.json() == {"id": "SKU-001", "total": 40, "disponivel": 0, "reservada": 30, "bloqueada": 10}

    liberada = client.post(f"/reservas/{reserva_id}/liberar")
    assert liberada.status_code == 200
    assert liberada.json()["status"] == "LIBERADA"
    resumo = client.get("/produtos/SKU-001")
    assert resumo.json() == {"id": "SKU-001", "total": 40, "disponivel": 30, "reservada": 0, "bloqueada": 10}

    liberado = client.post(f"/bloqueios/{bloqueio_id}/liberar")
    assert liberado.status_code == 200
    assert liberado.json()["status"] == "LIBERADO"
    resumo = client.get("/produtos/SKU-001")
    assert resumo.json() == {"id": "SKU-001", "total": 40, "disponivel": 40, "reservada": 0, "bloqueada": 0}

    assert client.get(f"/reservas/{reserva_id}").json()["status"] == "LIBERADA"
    assert client.get(f"/bloqueios/{bloqueio_id}").json()["status"] == "LIBERADO"


def test_erros_de_regra_viram_codigos_http(client):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})

    assert client.get("/produtos/NAO-EXISTE").status_code == 404
    assert client.get("/reservas/nao-existe").status_code == 404
    assert client.get("/bloqueios/nao-existe").status_code == 404
    assert client.post("/reservas/nao-existe/liberar").status_code == 404
    assert client.post("/bloqueios/nao-existe/liberar").status_code == 404

    saida = client.post("/produtos/SKU-001/saida", json={"quantidade": 11})
    assert saida.status_code == 409
    assert "Estoque insuficiente" in saida.json()["detail"]

    assert client.post("/produtos/SKU-001/reservas", json={"quantidade": 11, "solicitacao_id": "P"}).status_code == 409
    assert client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 11}).status_code == 409

    # as tentativas inválidas não alteraram o estoque
    assert client.get("/produtos/SKU-001").json()["disponivel"] == 10


def test_reserva_e_bloqueio_tem_rotas_proprias(client):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})
    reserva_id = client.post(
        "/produtos/SKU-001/reservas", json={"quantidade": 2, "solicitacao_id": "PED-1"}
    ).json()["id"]
    bloqueio_id = client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 3}).json()["id"]

    # o id de uma reserva não serve nas rotas de bloqueio, e vice-versa
    assert client.get(f"/bloqueios/{reserva_id}").status_code == 404
    assert client.post(f"/bloqueios/{reserva_id}/liberar").status_code == 404
    assert client.get(f"/reservas/{bloqueio_id}").status_code == 404
    assert client.post(f"/reservas/{bloqueio_id}/liberar").status_code == 404
    assert client.get("/produtos/SKU-001").json()["disponivel"] == 5


def test_liberar_duas_vezes_retorna_409(client):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})
    reserva_id = client.post(
        "/produtos/SKU-001/reservas", json={"quantidade": 4, "solicitacao_id": "PED-1"}
    ).json()["id"]
    bloqueio_id = client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 3}).json()["id"]

    assert client.post(f"/reservas/{reserva_id}/liberar").status_code == 200
    assert client.post(f"/reservas/{reserva_id}/liberar").status_code == 409
    assert client.post(f"/bloqueios/{bloqueio_id}/liberar").status_code == 200
    assert client.post(f"/bloqueios/{bloqueio_id}/liberar").status_code == 409
    assert client.get("/produtos/SKU-001").json()["disponivel"] == 10


@pytest.mark.parametrize(
    "corpo",
    [{"quantidade": 0}, {"quantidade": -5}, {"quantidade": 2.5}, {"quantidade": "10"}, {"quantidade": True}, {}],
)
def test_quantidade_invalida_retorna_422(client, corpo):
    assert client.post("/produtos/SKU-001/entrada", json=corpo).status_code == 422


@pytest.mark.parametrize("corpo", [{"quantidade": 1}, {"quantidade": 1, "solicitacao_id": "   "}])
def test_reserva_exige_solicitacao(client, corpo):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})
    assert client.post("/produtos/SKU-001/reservas", json=corpo).status_code == 422


def test_bloqueio_nao_exige_solicitacao(client):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})
    resposta = client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 1})
    assert resposta.status_code == 201
    assert resposta.json()["solicitacao_id"] is None


def test_listar_reservas_e_bloqueios_do_produto(client):
    client.post("/produtos/SKU-001/entrada", json={"quantidade": 10})
    r1 = client.post("/produtos/SKU-001/reservas", json={"quantidade": 3, "solicitacao_id": "PED-1"}).json()
    client.post("/produtos/SKU-001/reservas", json={"quantidade": 2, "solicitacao_id": "PED-2"})
    b1 = client.post("/produtos/SKU-001/bloqueios", json={"quantidade": 1}).json()
    client.post(f"/reservas/{r1['id']}/liberar")

    todas = client.get("/produtos/SKU-001/reservas").json()
    ativas = client.get("/produtos/SKU-001/reservas", params={"apenas_ativas": True}).json()
    assert len(todas) == 2
    assert [r["solicitacao_id"] for r in ativas] == ["PED-2"]

    assert [b["id"] for b in client.get("/produtos/SKU-001/bloqueios").json()] == [b1["id"]]
    assert client.get("/produtos/SKU-001/bloqueios", params={"apenas_ativos": True}).json()[0]["id"] == b1["id"]

    assert client.get("/produtos/NAO-EXISTE/reservas").status_code == 404
    assert client.get("/produtos/NAO-EXISTE/bloqueios").status_code == 404


def test_listar_produtos_paginado(client):
    for sku in ["SKU-A", "SKU-B", "SKU-C"]:
        client.post(f"/produtos/{sku}/entrada", json={"quantidade": 5})
    client.post("/produtos/SKU-A/reservas", json={"quantidade": 2, "solicitacao_id": "PED-1"})

    pagina1 = client.get("/produtos", params={"limite": 2}).json()
    assert [p["id"] for p in pagina1["itens"]] == ["SKU-A", "SKU-B"]
    assert pagina1["itens"][0] == {"id": "SKU-A", "total": 5, "disponivel": 3, "reservada": 2, "bloqueada": 0}
    assert pagina1["proximo"] == "SKU-B"

    pagina2 = client.get("/produtos", params={"limite": 2, "depois_de": pagina1["proximo"]}).json()
    assert [p["id"] for p in pagina2["itens"]] == ["SKU-C"]
    assert pagina2["proximo"] is None


def test_listar_produtos_filtra_por_prefixo(client):
    for sku in ["CAM-1", "CAM-2", "SAP-1"]:
        client.post(f"/produtos/{sku}/entrada", json={"quantidade": 1})
    resposta = client.get("/produtos", params={"prefixo": "CAM"}).json()
    assert [p["id"] for p in resposta["itens"]] == ["CAM-1", "CAM-2"]


@pytest.mark.parametrize("limite", [0, -1, 101])
def test_listar_produtos_rejeita_limite_invalido(client, limite):
    assert client.get("/produtos", params={"limite": limite}).status_code == 422


def test_swagger_usa_os_nomes_do_case(client):
    assert client.get("/docs").status_code == 200
    esquema = client.get("/openapi.json").json()
    resumos = {
        operacao.get("summary")
        for caminho in esquema["paths"].values()
        for operacao in caminho.values()
        if isinstance(operacao, dict)
    }
    for nome in ["Entrada", "Saída", "Reservar", "Bloquear", "Liberar reserva", "Liberar bloqueio", "Consultar produto"]:
        assert nome in resumos

# Testes: o que cada caso verifica

Rodar tudo: `pytest -v`. Rodar um arquivo: `pytest tests/test_consistencia.py -v`.

Total: 122 casos. A parametrização expande alguns testes em vários casos (por exemplo, o mesmo teste rodando nas 4 operações).

## Como o banco é isolado

- Cada teste recebe um **arquivo SQLite novo** em pasta temporária (`session_factory`, em `tests/conftest.py`), apagado ao fim. Nenhum teste enxerga dados de outro e o `estoque.db` real nunca é tocado.
- Os testes da API trocam a dependência `get_db` pelo banco temporário (`client`). O `TestClient` é usado sem `with`, então o *lifespan* do app não roda e nenhum banco real é criado.
- Cada requisição da API abre uma sessão nova, então os testes da API também provam que o dado foi **gravado** (e não apenas guardado na memória da sessão).

## Mapa dos testes

### `test_servicos.py`: regras de negócio, direto no `services.py` (51)

| Teste | Objetivo |
|---|---|
| entrada_cria_o_produto_e_acumula | A entrada cria o produto se não existe e soma ao total |
| saida_reduz_o_total | Saída retira do total |
| saida_pode_retirar_exatamente_o_disponivel | Valor-limite da saída |
| saida_acima_do_disponivel_falha_sem_alterar_o_estoque | Saída maior que o disponível é recusada |
| saida_nao_consome_unidades_reservadas_nem_bloqueadas | Só unidades disponíveis podem sair |
| reservar_move_unidades_do_disponivel_para_reservada | Reservar tira do disponível, põe na reservada e devolve a reserva com id |
| bloquear_move_unidades_do_disponivel_para_bloqueada | Idem para bloqueio (solicitação opcional) |
| varias_reservas_e_bloqueios_tem_ids_proprios | Várias reservas e bloqueios no mesmo produto, cada um com seu id |
| reservar_e_bloquear_acima_do_disponivel_falham... | Pedido acima do disponível é recusado |
| pode_reservar_exatamente_o_disponivel | Valor-limite da reserva |
| liberar_reserva / liberar_bloqueio_devolve... | Liberar devolve a quantidade ao disponível |
| liberacao_e_independente_entre_reservas | Liberar uma reserva não mexe nas outras |
| liberar_reserva_nao_afeta_os_bloqueios | Reserva e bloqueio não se misturam |
| liberar_reserva / liberar_bloqueio_duas_vezes... | Liberar de novo é recusado e a quantidade não volta em dobro |
| liberar_reserva_ou_bloqueio_inexistente | Id desconhecido dá "não encontrada" |
| reserva_e_bloqueio_nao_se_liberam_pelo_id_um_do_outro | O id de uma reserva não serve para liberar bloqueio, e vice-versa |
| cenario_completo_do_exemplo | O exemplo 100 / 30 / 10 / 60 de ponta a ponta |
| quantidade_invalida_e_rejeitada (7 casos) | Zero, negativo, `True`, decimal, texto e valores acima do limite (inclusive 2⁶³) são recusados na entrada |
| quantidade_no_limite_maximo_e_aceita | Valor-limite: exatamente 1.000.000 unidades é aceito |
| operacoes_em_produto_inexistente | Saída, reserva, bloqueio, consulta e listagens dão "produto não encontrado" |
| consultar_reserva_e_bloqueio_por_id | Consulta por id, com e sem sucesso |
| listar_reservas / listar_bloqueios_com_filtro | O filtro de ativos mostra só os não liberados |
| listar_produtos_ordenado_por_id_e_respeita_o_limite | Ordem por id e corte pelo limite |
| listar_produtos_traz_as_quantidades | A listagem inclui as quatro quantidades |
| listar_produtos_sem_dados_e_limite_invalido | Lista vazia e limite fora de 1..50 |
| listar_produtos_nos_valores_limite_1_e_50 | Os extremos válidos do limite |
| entrada_rejeita_id_de_produto_invalido (12 casos) | Espaço, aspas, SQL injection, acento, vazio e mais de 64 caracteres são recusados e não criam produto |
| entrada_aceita_id_de_produto_valido (4 casos) | Ids válidos passam, inclusive com 64 caracteres |

### `test_consistencia.py`: depois de um erro, o estoque fica como estava (25)

| Teste | Objetivo |
|---|---|
| quantidade_invalida_em_qualquer_operacao_nao_altera_o_estoque (16) | 4 quantidades inválidas (0, -1, `True` e acima do limite) × 4 operações. Sem a validação, `saida(-1)` aumentaria o estoque |
| pedido_acima_do_disponivel_nao_altera_o_estoque (3) | Pedir uma unidade a mais que o disponível é recusado sem mudar nada |
| liberar_reserva_duas_vezes... / liberar_bloqueio_duas_vezes... (2) | A segunda liberação é recusada e preserva o estoque e a data da primeira |
| apos_varios_erros_seguidos_a_proxima_operacao_valida_funciona | Depois de erros de tipos diferentes o estoque é o mesmo e o próximo pedido válido dá o resultado exato |
| varias_reservas_e_bloqueios_liberados_fora_de_ordem | Cada liberação devolve só a quantidade da própria reserva ou bloqueio |
| unidades_liberadas_podem_ser_reservadas_e_bloqueadas_de_novo | Liberar de fato devolve as unidades para uso |
| produtos_sao_independentes_entre_si | Nada vaza de um produto para outro (saldos, listagens, liberações) |

### `test_concorrencia.py`: threads ao mesmo tempo (1)

| Teste | Objetivo |
|---|---|
| reservas_simultaneas_nao_ultrapassam_o_estoque | 50 tentativas de reservar 1 unidade para 30 em estoque: exatamente 30 passam. Cada thread usa a própria sessão, e a fixture `conferencia_lenta` faz uma pausa depois de conferir o estoque, para forçar a corrida. Sem o lock o teste falha |

### `test_banco.py`: isolamento (5)

| Teste | Objetivo |
|---|---|
| o_banco_dos_testes_nao_e_o_do_projeto | Nenhum teste grava no `estoque.db` real |
| cada_teste_comeca_com_o_banco_vazio (3 repetições) | O mesmo teste, repetido, sempre parte do zero |
| a_api_grava_no_banco_isolado | As requisições HTTP caem no banco temporário |

### `test_api.py`: rotas, códigos HTTP e formato (40)

| Teste | Objetivo |
|---|---|
| fluxo_completo_pela_api | Entrada, reserva, bloqueio, saída e as duas liberações pelo HTTP, conferindo o resumo a cada passo |
| erros_de_regra_viram_codigos_http | 404 e 409 nas rotas, e o estoque intacto depois |
| reserva_e_bloqueio_tem_rotas_proprias | Os ids não se misturam entre as rotas |
| liberar_duas_vezes_retorna_409 | Liberação duplicada dá 409 |
| quantidade_invalida_retorna_422 (6) | Quantidade inválida na entrada |
| reserva_exige_solicitacao (2) / bloqueio_nao_exige_solicitacao | Regras da solicitação |
| listar_reservas_e_bloqueios_do_produto | Listagens, filtros e 404 |
| listar_produtos / rejeita_limite_invalido (3) | Listagem ordenada e limite fora de 1..50 |
| id_de_produto_invalido_retorna_422... (7) | Id perigoso na entrada e na consulta |
| swagger_usa_os_nomes_do_case | O Swagger mostra Entrada, Saída, Reservar, Bloquear, Liberar, Consultar |
| quantidade_invalida_retorna_422_em_toda_rota_de_escrita (8) | 0 e -5 nas 4 rotas que mexem no estoque, e o estoque fica igual |
| operacao_em_produto_inexistente_retorna_404... (3) | Saída, reserva e bloqueio em produto inexistente: 404 e nada criado |
| quantidade_acima_do_limite_retorna_422 (2) | 1.000.001 e 2⁶³ dão 422 e nada é criado (antes, 2⁶³ dava erro 500) |
| quantidade_no_limite_maximo_e_aceita | Exatamente 1.000.000 unidades é aceito pela API |

## Limite de quantidade

Cada operação aceita de 1 a 1.000.000 unidades (`QUANTIDADE_MAXIMA`, em `services.py`). O valor é uma premissa minha, porque
o enunciado não define um. O teto existe porque uma quantidade acima de 2⁶³−1 (9.223.372.036.854.775.807) passava na
validação e estourava no SQLite com `OverflowError` (confirmado gravando direto com `sqlite3`), o que resultava em erro 500. Hoje a API
responde 422, e os testes acima verificam o limite exato e o primeiro valor acima dele.

## Como provar que os testes protegem (teste de mutação manual)

Estrague o código de propósito, rode `pytest` e confira se algum teste falha. Se nenhum falhar, a suíte não protege aquela regra. Desfaça a alteração depois de cada linha.

| Defeito a injetar | Teste que deve falhar |
|---|---|
| Em `saida`, apagar `_validar_quantidade(quantidade)` | `quantidade_invalida_em_qualquer_operacao...[saida-*]` |
| Em `reservar`, apagar `_validar_quantidade(quantidade)` | `quantidade_invalida_em_qualquer_operacao...[reservar-*]` |
| Em `_validar_quantidade`, tirar o teto (`<= QUANTIDADE_MAXIMA`) | `quantidade_invalida_em_qualquer_operacao...[*-1000001]` e `quantidade_invalida_e_rejeitada` |
| Em `listar_reservas`, devolver as reservas de todos os produtos | `produtos_sao_independentes_entre_si` |
| Em `liberar_reserva`, gravar `liberada_em` antes de levantar `ReservaJaLiberada` | `liberar_reserva_duas_vezes_nao_altera...` |
| Em `_exigir_disponivel`, trocar `>` por `>=` | `pode_reservar_exatamente_o_disponivel` e outros |
| Em `Produto.reservada`, somar reservas de qualquer status | vários testes, entre eles `varias_reservas_e_bloqueios_liberados_fora_de_ordem` |
| Remover o `with _lock:` das operações | `reservas_simultaneas_nao_ultrapassam_o_estoque` |
| Em `liberar_reserva`, apagar o `db.commit()` | `fluxo_completo_pela_api` (os testes de serviço não pegam, porque reutilizam a mesma sessão) |

## O que os testes não garantem

- **Persistência nos testes de serviço.** Eles reutilizam uma sessão, então um `commit` esquecido só seria pego pelos testes da API e pelo de concorrência, que usam sessão nova.
- **Vários processos.** O lock é de um processo só (limitação já documentada).
- **Leitura consistente durante escrita.** O lock em `consultar_produto` evita um resumo "misturado", mas não há teste que falhe de forma determinística sem ele.
- **Chave estrangeira.** O SQLite não aplica `FOREIGN KEY` por padrão (exigiria `PRAGMA foreign_keys=ON`); nenhum teste depende disso.
- **`solicitacao_id` no serviço.** Quem valida é o Pydantic (API) e o `NOT NULL` do banco; chamar `services.reservar(..., None)` direto resulta em erro de banco, não em erro de domínio.
- **Volume e desempenho.** Não há teste com muitos produtos ou milhões de reservas.

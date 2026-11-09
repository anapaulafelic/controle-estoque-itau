# Controle de Estoque

Uma API para controlar o estoque de produtos, feita em Python com FastAPI, SQLAlchemy, Pydantic e SQLite.
Para usar e demonstrar, basta abrir a página interativa (Swagger) no navegador.

| Documento | Conteúdo |
|---|---|
| `README.md` | Este arquivo: visão geral, estrutura, decisões, premissas, limitações, como executar e o que mudaria em produção |
| [`TESTES.md`](TESTES.md) | O que cada teste verifica e como o banco dos testes é isolado |
| [`USO_DE_IA.md`](USO_DE_IA.md) | Principais prompts e a análise do uso de IA |
| [`VISAO_DE_ENGENHARIA.md`](VISAO_DE_ENGENHARIA.md) | Os 5 aspectos mais importantes para a qualidade e a evolução da solução |

No fim deste arquivo há um [glossário](#glossário) com os termos técnicos em palavras simples.

## 1. Visão geral

Para cada produto, o sistema guarda quatro quantidades:

| Quantidade | O que significa |
|---|---|
| **total** | tudo o que existe no estoque |
| **disponível** | o que pode ser usado agora |
| **reservada** | o que está separado para um pedido |
| **bloqueada** | o que está travado e não pode ser usado |

Existe uma regra que **nunca** pode ser quebrada: `total = disponível + reservada + bloqueada`.

Cada reserva e cada bloqueio recebe um código próprio (`id`). Com esse código dá para consultá-lo e liberá-lo sem
mexer nos outros. Um produto pode ter várias reservas e vários bloqueios ao mesmo tempo.

| Funcionalidade do case | Rota | Resposta |
|---|---|---|
| Entrada | `POST /produtos/{id}/entrada` | 200 |
| Saída | `POST /produtos/{id}/saida` | 200 |
| Reservar | `POST /produtos/{id}/reservas` | 201, com o `id` da reserva |
| Bloquear | `POST /produtos/{id}/bloqueios` | 201, com o `id` do bloqueio |
| Liberar | `POST /reservas/{id}/liberar` e `POST /bloqueios/{id}/liberar` | 200 |
| Consultar | `GET /produtos/{id}`, `GET /reservas/{id}`, `GET /bloqueios/{id}` | 200 |

Também criei três listagens que o case não pede: `GET /produtos?limite=` (até 50 produtos),
`GET /produtos/{id}/reservas` e `GET /produtos/{id}/bloqueios`. Elas existem porque quem perdesse o `id` de uma reserva
ou de um bloqueio não teria outro jeito de encontrá-lo.

**Exemplo:** entram 100 unidades, reservamos 30 e bloqueamos 10. O disponível fica em **60**. Uma saída de 60 deixa
**total 40 e disponível 0**. Se liberarmos a reserva, o disponível volta a **30**.

**Quando algo dá errado, a API responde:** `404` (produto, reserva ou bloqueio não existe), `409` (estoque
insuficiente, ou item que já foi liberado) e `422` (quantidade ou identificador inválido).

## 2. Estrutura do projeto

São quatro partes, sem pastas ou camadas extras:

```
app/
├── main.py        liga tudo e transforma os erros de regra em respostas HTTP (404, 409, 422)
├── routes.py      as rotas: recebem o pedido e chamam o serviço. Não têm regra de negócio
├── schemas.py     o formato dos dados que entram e saem da API (e o que aparece no Swagger)
├── services.py    TODAS as regras do estoque: entrada, saída, reservar, bloquear, liberar, consultar
├── models.py      as tabelas do banco: Produto, Reserva e Bloqueio
├── exceptions.py  os erros de regra (estoque insuficiente, reserva já liberada, ...)
└── database.py    a conexão com o banco SQLite
tests/             os testes automáticos
```

**O caminho de um pedido:**

1. A rota (`routes.py`) recebe o pedido, e o `schemas.py` confere se os dados têm o formato certo.
2. A rota chama uma função do `services.py`, que aplica as regras do estoque.
3. O `services.py` lê e grava no banco usando as classes do `models.py`.
4. Se alguma regra for violada, o `services.py` gera um erro (`exceptions.py`) e o `main.py` o transforma em uma
   resposta HTTP.

**O modelo:** um produto é "dono" das suas reservas e dos seus bloqueios.

```
Produto (id, total)
 ├── várias Reservas   (id, pedido, quantidade, status ATIVA ou LIBERADA, datas)
 └── vários Bloqueios  (id, pedido opcional, quantidade, status ATIVO ou LIBERADO, datas)
```

## 3. Principais decisões e por quê

1. **O produto guarda só o `total`.** A reservada, a bloqueada e a disponível são calculadas somando as reservas e os
   bloqueios que estão ativos. Assim os números nunca ficam diferentes entre si, porque todos nascem do mesmo lugar.
   Liberar é só mudar o status para "liberada", e o histórico continua guardado.
2. **Reserva e Bloqueio são separados**, cada um com a sua própria liberação. A reserva vai ganhar um passo a mais
   (efetivar, descrito na seção 7) que o bloqueio não tem. Juntar os dois obrigaria a desfazer isso depois.
3. **Toda operação segue a mesma ordem:** conferir os dados, travar, conferir a regra do estoque, alterar e salvar.
   Como a regra é conferida **antes** de alterar, um pedido recusado não muda nada no estoque.
4. **Uma trava para evitar conflito entre pedidos simultâneos.** Sem ela, dois pedidos ao mesmo tempo poderiam ver
   "10 disponíveis" e cada um reservar 8. A trava faz uma operação de cada vez conferir e alterar o estoque. No código,
   ela se chama `Lock`.
5. **A validação acontece em três lugares:** o Pydantic confere o formato (só aceita número inteiro maior que zero;
   recusa `true`, `2.5` e `"10"`), o serviço confere de novo, e o próprio banco tem regras que recusam quantidade
   negativa ou zero. Se uma falhar, a próxima segura.
6. **O código do produto (SKU) é restrito:** só letras, números, hífen e sublinhado, sem espaços, até 64 caracteres.
   Isso evita nomes estranhos e tentativas de enviar comandos maliciosos pelo texto (o chamado *SQL injection*). A
   proteção principal contra isso é o SQLAlchemy, que nunca cola o texto digitado dentro do comando do banco. A lista de
   caracteres permitidos é uma segunda proteção.
7. **A entrada cria o produto** se ele ainda não existir, porque o case não tem uma função de cadastro.
8. **Usei os mesmos nomes do enunciado** em funções, rotas e no Swagger: `entrada`, `saida`, `reservar`, `bloquear`,
   `liberar` e `consultar`.
9. **Testes com banco isolado:** cada teste usa um banco novo, que é apagado no fim. São 122 casos (ver `TESTES.md`).

## 4. Premissas

- Existe um único local de estoque, e as quantidades são números inteiros.
- O produto passa a existir na primeira entrada. O código dele (SKU) segue o formato da decisão 6.
- A reserva exige o código do pedido (`solicitacao_id`), porque o enunciado a define "para uma solicitação/pedido".
  No bloqueio esse código é opcional.
- Liberar é sempre total e definitivo. Um item liberado não volta a ficar ativo; para reservar de novo, cria-se outra
  reserva.
- A saída só retira unidades **disponíveis**. As reservadas e as bloqueadas não são tocadas.
- Quem reserva ou bloqueia guarda o `id` recebido (e há as listagens por produto para o caso de perdê-lo).
- Cada operação aceita de **1 a 1.000.000** unidades. O enunciado não define um valor; escolhi esse teto para barrar
  números absurdos (que davam erro no banco). Ele é fácil de mudar (`QUANTIDADE_MAXIMA`, em `services.py`).
- Não há login nem controle de acesso. As datas são gravadas em UTC (horário universal).

## 5. Limitações conhecidas

- **Sem logs e sem rastreabilidade.** O sistema não registra quem fez cada operação nem guarda um histórico das
  entradas e saídas (só o total é atualizado).
- **Vários registros para o mesmo pedido e produto.** O sistema aceita mais de uma reserva (ou bloqueio) para o mesmo
  pedido e o mesmo produto. Cada uma é um registro independente, com seu próprio `id`. Isso é permitido de propósito,
  porque o enunciado fala em várias reservas e bloqueios, mas pode gerar muitos registros repetidos para um mesmo
  pedido.
- **Só o código do produto tem formato definido.** O código do pedido (`solicitacao_id`) é um texto livre de até 100
  caracteres. Um formato definido ajudaria nas validações e nos testes. Os `id` de reservas e bloqueios são gerados
  pelo próprio sistema.
- **A trava só funciona em uma instância.** Se o sistema rodar em vários processos ao mesmo tempo, ela não protege.
- **A consulta de um produto fica mais lenta quanto mais reservas ele tem.** O código carrega todas as reservas e
  bloqueios do produto (inclusive os já liberados) e soma. Com milhões de registros, isso pesa.
- **A listagem de produtos mostra só os 50 primeiros**, sem páginas e sem filtros.
- **Não há busca por pedido, nem prazo de validade para reservas.** Também não há proteção contra o mesmo pedido enviado
  duas vezes (por exemplo, um clique duplo).
- **O SQLite** aceita uma gravação por vez. As tabelas são criadas ao iniciar o sistema, sem controle de mudanças da
  estrutura do banco.

## 6. Como executar

Precisa do Python 3.10 ou mais novo (foi executado e testado na 3.14).

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Se o PowerShell bloquear a ativação, rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra **http://127.0.0.1:8000/docs** no navegador (o endereço `/` leva para lá). O arquivo do banco, `estoque.db`, é
criado sozinho na primeira vez. Para começar do zero, pare o sistema e apague esse arquivo.

**Roteiro rápido no Swagger:**

1. `Entrada` com o produto `SKU-001` e quantidade `100`.
2. `Reservar` 30 (informe um pedido, como `PED-1`) e guarde o `id` devolvido.
3. `Bloquear` 10 e guarde o `id`.
4. `Consultar produto`: total 100, disponível 60, reservada 30, bloqueada 10.
5. `Liberar reserva` com o `id` guardado e consulte de novo: disponível 90.

**Testes:** rode `pytest` (ou `pytest -v`). O resultado esperado é `122 passed`. Pode aparecer um aviso amarelo sobre uma biblioteca do
teste; ele não afeta o resultado.

## 7. O que eu faria diferente em produção

**Para o estoque continuar certo com muita gente usando ao mesmo tempo**
- Trocar o SQLite por um banco profissional, como o **PostgreSQL**, e deixar que ele proteja o produto: enquanto uma
  operação está em andamento, a linha do produto fica travada para as outras. Isso funciona mesmo com vários processos.
- Testar esse cenário com o banco real.

**Para continuar rápido com muitos dados**
- Guardar já calculadas as quantidades reservada e bloqueada, atualizando-as junto com cada operação. Assim a consulta
  não precisa somar tudo toda vez.
- Busca com filtros e páginas para **produtos, reservas e bloqueios** (por exemplo, por pedido ou por status), para
  facilitar a localização dos registros.

**Novas funções**
- **Efetivar (consumir) reserva.** A reserva passa para o estado "efetivada" e as unidades saem do estoque de uma vez,
  em uma única operação. O total e a reservada diminuem juntos, e o disponível não muda. As unidades **nunca voltam ao
  disponível** no meio do caminho, então nenhuma outra operação consegue "pegar" aquilo que já está destinado à
  saída da compra. (Hoje, para chegar ao mesmo resultado, seria preciso liberar a reserva e só depois dar saída, e
  nesse intervalo outra operação poderia ficar com as unidades.)
- **Inativar produto,** sem apagar o histórico dele.
- **Vários registros para o mesmo pedido e produto:** somar as quantidades antes de enviar ao estoque, para ficar
  uma reserva (ou bloqueio) só por pedido e produto.
- **Definir um formato para o código do pedido** (`solicitacao_id`), como já existe para o produto.
- Prazo de validade para reservas, liberação parcial e vários locais de estoque.

**Para acompanhar o que acontece**
- **Logs e auditoria:** registrar cada operação com data e hora, e um código que acompanha o pedido do começo ao fim.
- **Rastreabilidade das ações dos usuários:** exigir login e guardar quem fez cada operação.
- **Histórico de movimentações:** guardar cada entrada, saída, reserva, bloqueio e liberação, sem nunca apagar,
  para conferir e explicar de onde veio cada número.
- **Proteção contra pedido repetido:** se o cliente enviar a mesma operação duas vezes, ela não pode ser feita em
  dobro.

**Para operar o sistema**
- Controle de mudanças da estrutura do banco (migrations), configuração por variáveis de ambiente e empacotamento
  com Docker.
- Rodar os testes automaticamente a cada alteração (GitHub Actions).
- Monitoramento do sistema (saúde, erros e tempo de resposta) e limite de requisições por usuário.

## Glossário

| Termo | Em palavras simples |
|---|---|
| **API** | Um programa que outros programas (ou pessoas, pelo Swagger) usam enviando pedidos pela internet |
| **Swagger** | A página que o FastAPI monta sozinho, onde se testa cada rota clicando |
| **FastAPI** | A ferramenta Python que cria a API |
| **SQLAlchemy** | Faz a ponte entre o código Python e o banco de dados, sem escrever SQL na mão |
| **Pydantic** | Confere se os dados que chegam têm o formato certo (por exemplo, número inteiro maior que zero) |
| **SQLite** | Um banco de dados simples, que fica em um único arquivo (`estoque.db`) |
| **PostgreSQL** | Um banco de dados profissional, usado em sistemas grandes |
| **Trava (`Lock`)** | Faz uma operação de cada vez passar por um trecho do código, para que duas não se atrapalhem |
| **SQL injection** | Ataque que tenta enviar comandos para o banco escondidos dentro de um texto digitado |
| **`id` (código único)** | O código que identifica cada reserva e cada bloqueio, gerado pelo sistema |
| **Status** | A situação de uma reserva ou bloqueio: ativa/ativo ou liberada/liberado |
| **Log** | O registro do que o sistema fez e quando, usado para investigar problemas |
| **Auditoria** | Poder conferir depois quem fez o quê e quando |
| **Migrations** | Um jeito de controlar e aplicar as mudanças na estrutura do banco ao longo do tempo |

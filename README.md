# Controle de Estoque

API para controlar o estoque de produtos, feita em Python com FastAPI, SQLAlchemy, Pydantic e SQLite.
Para usar e demonstrar, basta abrir a página interativa (Swagger) no navegador. A interface de usuário (Frontend) não foi desenvolvida por uma decisão de escopo. Item 6 da documentação.

| Documento                                          | Conteúdo                                                                                                         |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `README.md`                                        | Este arquivo: visão geral, estrutura, decisões, premissas, limitações, como executar e o que mudaria em produção |
| [`TESTES.md`](TESTES.md)                           | O que cada teste verifica e como o banco dos testes é isolado                                                    |
| [`USO_DE_IA.md`](USO_DE_IA.md)                     | Principais prompts e a análise do uso de IA                                                                      |
| [`VISAO_DE_ENGENHARIA.md`](VISAO_DE_ENGENHARIA.md) | Os 5 aspectos mais importantes para a qualidade e a evolução da solução                                          |

## 1. Visão geral

Para cada produto, o sistema guarda quatro quantidades:

| Quantidade     | O que significa                         |
| -------------- | --------------------------------------- |
| **total**      | tudo o que existe no estoque            |
| **disponível** | o que pode ser usado agora              |
| **reservada**  | o que está separado para um pedido      |
| **bloqueada**  | o que está travado e não pode ser usado |

Existe uma regra que **nunca** pode ser quebrada: `total = disponível + reservada + bloqueada`.

Cada reserva e cada bloqueio recebe um código próprio (`id`). Com esse código dá para consultá-lo e liberá-lo sem
mexer nos outros. Um produto pode ter várias reservas e vários bloqueios ao mesmo tempo.

| Funcionalidade do case | Rota                                                              | Resposta                    |
| ---------------------- | ----------------------------------------------------------------- | --------------------------- |
| Entrada                | `POST /produtos/{id}/entrada`                                     | 200                         |
| Saída                  | `POST /produtos/{id}/saida`                                       | 200                         |
| Reservar               | `POST /produtos/{id}/reservas`                                    | 201, com o `id` da reserva  |
| Bloquear               | `POST /produtos/{id}/bloqueios`                                   | 201, com o `id` do bloqueio |
| Liberar                | `POST /reservas/{id}/liberar` e `POST /bloqueios/{id}/liberar`    | 200                         |
| Consultar              | `GET /produtos/{id}`, `GET /reservas/{id}`, `GET /bloqueios/{id}` | 200                         |

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
4. Se alguma regra for violada, o `services.py` gera um erro (`exceptions.py`) e o `main.py` o transforma em uma resposta HTTP.

**O modelo:** um produto é "dono" das suas reservas e dos seus bloqueios.

```
Produto (id, total)
 ├── várias Reservas   (id, pedido, quantidade, status ATIVA ou LIBERADA, datas)
 └── vários Bloqueios  (id, pedido opcional, quantidade, status ATIVO ou LIBERADO, datas)
```

## 3. Principais decisões e por quê

1. **O produto guarda só o `total`.** Os valores de reservado, bloqueado e disponível são calculados somando as reservas e os
   bloqueios que estão ativos. Assim os números nunca ficam diferentes entre si, porque todos nascem do mesmo lugar.
2. **Reserva e Bloqueio possuem funções próprias**, cada um com a sua própria liberação. A reserva poderia ganhar um passo a mais
   (efetivar, descrito na seção 7), manter os dois desacoplados, facilita essa implementação futura.
3. **Toda operação segue a mesma ordem:** conferir os dados, travar, conferir a regra do estoque, alterar e salvar.
   Como a regra é conferida **antes** de alterar, um pedido recusado não muda o estoque.
4. **Uma trava para evitar conflito entre pedidos simultâneos.** Sem ela, dois pedidos ao mesmo tempo poderiam ver
   "10 disponíveis" e cada um reservar 8. A trava faz uma operação de cada vez conferir e alterar o estoque. No código,
   ela se chama `Lock`.
5. **A validação acontece em três lugares:** o Pydantic confere o formato (só aceita número inteiro maior que zero;
   recusa `true`, `2.5` e `"10"`), o serviço confere de novo, e o próprio banco tem regras que recusam quantidade
   negativa ou zero. Se uma falhar, a próxima segura.
6. **O código do produto (SKU) é restrito:** só letras, números, hífen e sublinhado, sem espaços, até 64 caracteres.
   Isso evita nomes estranhos e tentativas de enviar comandos maliciosos pelo texto (_SQL injection_). A
   proteção principal contra isso é o SQLAlchemy, que nunca cola o texto digitado dentro do comando do banco. A lista de
   caracteres permitidos é uma segunda proteção.
7. **A entrada cria o produto** se ele ainda não existir, porque o case não tem uma função de cadastro.
8. **Mantive os nomes do enunciado** em funções, rotas e no Swagger: `entrada`, `saida`, `reservar`, `bloquear`,
   `liberar` e `consultar`.
9. **Testes com banco isolado:** cada teste usa um banco novo, que é apagado no fim. São 122 casos (ver `TESTES.md`).

## 4. Premissas

- Existe um único local de estoque, e as quantidades são números inteiros.
- O produto passa a existir na primeira entrada. O código dele (SKU) segue o formato da decisão 6.
- A reserva exige o código do pedido (`solicitacao_id`), porque o enunciado a define "para uma solicitação/pedido".
  No bloqueio esse código é opcional.
- Liberar é sempre total e definitivo. Uma reserva liberada não volta a ficar ativa; para reservar de novo, cria-se outra
  reserva.
- A saída só retira unidades **disponíveis**. As reservadas e as bloqueadas não podem ser utilizadas pela saída.
- Quem reserva ou bloqueia guarda o `id` (incluí listagens por produto para o caso de perdê-lo).
- Cada operação aceita de **1 a 1.000.000** unidades. O enunciado não define um valor; escolhi esse teto para barrar
  números absurdos e evitar erro no banco. Para alterar (`QUANTIDADE_MAXIMA`, em `services.py`).
- Não estava previsto login nem controle de acesso. As datas são gravadas em UTC (horário universal).

## 5. Limitações conhecidas

- **Sem logs e sem rastreabilidade:** O sistema não registra quem realizou cada operação nem guarda um histórico completo de auditoria de entradas e saídas (apenas o total do produto é atualizado).
- **Vários registros para o mesmo pedido e produto:** O sistema aceita mais de uma reserva (ou bloqueio) para a mesma combinação de pedido e produto, gerando registros independentes. Optei por essa abordagem para atender ao enunciado de suportar "diversas reservas e bloqueios simultaneamente". Contudo, em produção, eu implementaria uma agregação prévia no aplicativo antes de acionar o estoque, enviando comandos consolidados.
- **Formato livre para códigos de pedido:** Apenas o código do produto (`produto_id`) possui validação rígida de formato. O `solicitacao_id` aceita texto livre de até 100 caracteres. Em uma evolução do projeto, definiria um padrão de máscara para facilitar validações e testes.
- **Concorrência limitada a uma única instância:** O mecanismo de trava atual protege as operações apenas enquanto o sistema rodar em um único processo/servidor. Em um ambiente escalado com múltiplos servidores, seria necessário utilizar uma trava centralizada (no banco de dados ou em cache distribuído).
- **Consulta pesada em grande escala:** O cálculo da quantidade disponível é feito dinamicamente, somando a lista de reservas e bloqueios no momento da leitura. Em um ambiente real com milhões de registros, essa abordagem deixaria as respostas lentas. Como melhoria, os totais poderiam ser armazenados diretamente no produto, os registros liberados movidos para uma tabela de histórico, ou as atualizações processadas via serviço de filas.
- **Listagem simplificada:** A consulta de produtos retorna no máximo 50 registros por vez, sem suporte a paginação dinâmica ou filtros avançados.
- **Regras avançadas de requisição:** O sistema não possui expiração automática para reservas pendentes (prazo de validade/TTL) nem proteção nativa contra requisições duplicadas enviadas acidentalmente (como um clique duplo).
- **Limitações do SQLite e ausência de migrações:** O banco SQLite processa uma gravação por vez. Além disso, as tabelas são recriadas ao iniciar o sistema, sem uma ferramenta de controle de alterações de estrutura do banco de dados (migrações).

## 6. Como executar e interagir com o sistema

Necessário Python 3.10 ou superior (foi executado e testado vs 3.14).
**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Se o PowerShell bloquear a ativação, rodar uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Como interagir com o sistema (Swagger):**
Como interagir com o sistema: Como esta solução foi desenvolvida com foco total no backend e nas regras de negócio (sem frontend acoplado), todas as interações com o estoque devem ser feitas consumindo a API. Você pode testar as rotas diretamente pelo Swagger/OpenAPI acessando um padrão "http://localhost:porta/docs", conforme orientações a seguir.

Acesse **http://127.0.0.1:8000/docs** no navegador.
O arquivo do banco, `estoque.db`, é criado automaticamente com a inicialização do projeto acima. Para iniciar um teste com base sem registros, pare o sistema e apague `estoque.db`.

**Roteiro rápido para um teste no Swagger:**

1. `Entrada` com o produto `SKU-001` e quantidade `100`.
2. `Reservar` 30 (informe um pedido, como `PED-1`) e guarde o `id` devolvido.
3. `Bloquear` 10 e guarde o `id`.
4. `Consultar produto`: Esperado = total 100, disponível 60, reservada 30, bloqueada 10.
5. `Liberar reserva` com o `id` guardado e consulte novamente: Esperado = disponível 90.

**Como rodar os testes automatizados:**
**Testes:** rode `pytest` (ou `pytest -v`) no terminal. O resultado esperado é `122 passed`. Pode aparecer um aviso amarelo sobre uma biblioteca do teste; ele não afeta o resultado.

## 7. O que eu faria diferente em produção

**Integridade do estoque, com número elevado de acessos**

- Trocar o SQLite por um banco mais utilizado em produção como o **PostgreSQL**, mais efetivos para proteção de transações no caso dos produtos: enquanto uma operação está em andamento, a linha do produto fica travada para as outras, mesmo com processos simultâneos.

**Desempenho e escalabilidade**

- Guardar já calculadas as quantidades reservada e bloqueada, atualizando-as junto com cada operação. Assim a consulta
  não precisa somar tudo toda vez.
- Busca com filtros e páginas para **produtos, reservas e bloqueios** (por exemplo, por pedido ou por status), para
  facilitar a localização dos registros e melhora da experiência do usuário.

**Novas funções e/ou ajustes**

- **Efetivar (consumir) reserva.** A reserva passa para o estado "efetivada" e as unidades saem do estoque diretamente, em uma única operação. O total e a reservada diminuem simultaneamente, e o disponível não é afetado durante a operação. (Hoje, para chegar ao mesmo resultado, seria preciso liberar a reserva e só depois dar saída, gerando o risco nesse intervalo, de outra operação interferir no processo.)
- **Inativar produto,** para manter o histórico.
- **Consolidação de pedidos (Vários registros para o mesmo pedido e produto):** somar as quantidades antes de enviar ao estoque, mantendo uma reserva (ou bloqueio) para combinações de "pedido e produto" que só alternam as quantidades.
- **Definir um formato para o código do pedido** (`solicitacao_id`), como já existe para o produto.
- Prazo de validade para reservas, liberação parcial e vários locais de estoque.

**Rastreabilidade e Auditoria**

- **Logs e auditoria:** registrar cada operação com data e hora, e um código que acompanha o pedido do começo ao fim.
- **Rastreabilidade das ações dos usuários:** exigir login e guardar quem fez cada operação.
- **Histórico de movimentações:** guardar cada entrada, saída, reserva, bloqueio e liberação, sem nunca apagar,
  para conferir e explicar de onde veio cada número.
- **Proteção contra pedido repetido:** para evitar repetições de registros, para casos de solicitações idênticas simultâneas.

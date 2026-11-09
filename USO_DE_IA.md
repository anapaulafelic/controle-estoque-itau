# Uso de IA

Usei o Claude (Anthropic) em uma conversa contínua, como parceiro para analisar o problema, gerar o código em
etapas e revisar o resultado. As decisões de escopo e de design foram minhas; li o que foi gerado, perguntei o que
não entendi, rodei os testes na minha máquina e corrigi o rumo quando o resultado não servia.

Os prompts abaixo são os que tiveram impacto relevante, transcritos com pequenas correções de ortografia.

## Principais prompts

### 1. Modelagem, antes de qualquer código

> Atue como engenheiro de software sênior especialista em Python. Analise o enunciado do case de Controle de Estoque,
> sem gerar código. Identifique entidades, relacionamentos, regras de negócio, validações e situações excepcionais.
> Proponha uma modelagem simples que permita múltiplas reservas e bloqueios por produto, com identificação individual
> e liberação independente. Explique as decisões e destaque o que preciso saber defender na entrevista.

**Impacto:** definiu as entidades e a regra central `total = disponível + reservada + bloqueada`, e propôs calcular as
quantidades a partir dos itens ativos em vez de armazená-las.

### 2. Projeto em etapas e arquitetura simples

> Com base na modelagem aprovada, proponha um projeto Python com FastAPI, SQLAlchemy, Pydantic e SQLite. Separe rotas,
> modelos, schemas, conexão com banco e regras de negócio. Mantenha a arquitetura simples, adequada a um case de até
> 3 horas. Evite abstrações desnecessárias. Gere os arquivos em etapas e explique a responsabilidade de cada um. Vamos
> usar Swagger para apresentar ao recrutador no final. Lembre de manter uma arquitetura bem simples (pedido do case),
> preciso saber explicar e compreender o código, e não montar uma arquitetura complexa.

**Impacto:** gerou a estrutura de quatro camadas, com a explicação da responsabilidade de cada arquivo.

### 3. Dúvida de design: como achar os ids?

> Perfeito. No sistema, não há uma opção para listar. Ele pressupõe que o id do produto, das reservas e dos bloqueios
> são conhecidos. Como seria a solução para esse caso num sistema real? Uma opção de listagem geral? Em um sistema
> muito grande, isso teria algum impacto de performance? Não precisa gerar código, só tirar essa dúvida, de forma
> direta e breve.

**Impacto:** levou às listagens por produto e à anotação, no README, do custo do resumo e da paginação como melhoria.

### 4. Refatoração para o vocabulário do case

> Vamos ajustar as funções. Refatore. Você alterou o nome das funcionalidades solicitadas no case. Vamos manter os
> nomes. Reservas, bloqueios... Não vamos unificar liberar retenções para reservas e bloqueios, pois, como melhoria
> futura, eles possuirão passos distintos. Da reserva, no futuro, será possível alterar para efetivado, mandando o
> total da reserva diretamente para a saída. Então mantenha o padrão DDD, com os nomes propostos no case, a menos que
> seja uma funcionalidade nova que estamos implementando.

**Impacto:** Reserva e Bloqueio viraram entidades separadas, cada uma com a sua liberação, e os nomes voltaram a ser os
do enunciado.

### 5. Segurança do identificador e listagem simplificada

> 1 - Entendi, nesse caso ele deveria permitir. Vamos ajustar só para não permitir caracteres perigosos em
> cibersegurança, evitando SQL injection, e não permitir textos com espaços. Consegui cadastrar um "teste teste" como
> código do produto. 2 - Vamos ajustar o campo listar produtos, para simplificar o modelo. Deixe só a opção de quantidade
> de itens até 50. E só o campo número. Uma paginação completa deverá entrar com os itens de melhoria no README.

**Impacto:** o identificador do produto passou a aceitar só letras, números, hífen e sublinhado (até 64), e a listagem
ficou com um único parâmetro, `limite`.

### 6. Revisão dos testes como QA

> Analise a eficiência dos testes já criados. Atue como engenheiro de QA especializado em Python e pytest. Analise a
> implementação e avalie os testes criados para cenários positivos, negativos e excepcionais. Teste consistência após
> operações inválidas, múltiplas reservas, bloqueios, liberações duplicadas e quantidades inválidas. Utilize banco
> isolado para os testes e explique o objetivo de cada caso.

**Impacto:** apontou lacunas reais nos testes e um defeito no código (ver a análise abaixo). Depois perguntei se a
quantidade de testes não seria exagerada e pedi para manter o simples: a suíte foi reduzida de 196 para 113 casos.

## Análise

### Onde a IA mais ajudou

- **Modelagem.** Identificar a regra central e a ideia de derivar as quantidades dos itens ativos, que elimina a
  possibilidade de os números divergirem.
- **Velocidade com explicação.** Gerar o esqueleto, o código e os testes em etapas, sempre dizendo a responsabilidade
  de cada arquivo e o que eu precisaria defender na entrevista.
- **Revisão crítica do próprio trabalho.** No papel de QA, a IA encontrou fraquezas nos testes que ela mesma tinha
  gerado e um defeito no código (descritos abaixo), e criou uma tabela de defeitos para injetar de propósito
  (`TESTES.md`).

### Onde discordei da IA (sugestões que modifiquei ou não usei)

- **Nomenclatura de funções e rotas.** A IA tinha criado nomes próprios. Pedi para voltar aos nomes do enunciado
  (Entrada, Saída, Reservar, Bloquear, Liberar e Consultar) nas funções, nas rotas e no Swagger. Motivo: é o
  vocabulário do case, o que facilita a avaliação e a minha explicação. Os nomes novos ficaram só nas funções que o
  case não pede (as listagens).
- **Estrutura do modelo: reserva e bloqueio juntos.** A IA unificou os dois numa só "retenção", com uma única forma de
  liberar. Não usei. A reserva vai ganhar um passo a mais (efetivar, mandando o total da reserva direto para a saída)
  que o bloqueio não tem, então juntá-los obrigaria a desfazer isso depois. Pedi duas entidades separadas, cada uma
  com a sua liberação.
- **Quantidade e escolha dos testes.** A IA chegou a 196 casos, com técnicas que eu não conseguiria explicar bem
  (leitura do banco por SQL direto, sequência de operações sorteadas, testes das regras do banco). Achei
  desproporcional para um case de 3 horas e pedi para manter o simples. Ficaram 113 casos, e mantive os testes
  principais, que consigo defender: as regras do enunciado, os erros, a consistência depois de uma operação recusada,
  a liberação repetida e os pedidos simultâneos.
- **Paginação completa na listagem de produtos.** Simplifiquei para um parâmetro `limite` de até 50, por pragmatismo.
  A paginação completa ficou como melhoria no README.
- **Código do produto livre.** A IA explicou que aceitar qualquer texto era coerente com o desenho (a entrada cria o
  produto). Eu decidi restringir os caracteres por segurança e para evitar códigos com espaços, e a IA implementou uma
  lista de caracteres permitidos.

### Erros, limitações e problemas que identifiquei

- **Desvio do enunciado.** A IA renomeou as funcionalidades do case e juntou reserva e bloqueio (ver acima). Percebi
  ao revisar o Swagger e pedi a correção.
- **Comandos para o ambiente errado.** As instruções iniciais usavam sintaxe de Bash (`&&`, `source`) e falharam no
  meu PowerShell. A IA corrigiu para o Windows.
- **Erro de digitação no modelo.** Um `order_by` apontava para `Bloqueio.criada_em`, mas a coluna se chama
  `criado_em`. Foi encontrado na revisão e corrigido.
- **Teste de pedidos simultâneos fraco.** O primeiro teste gerado passaria mesmo sem a trava (`Lock`), porque o
  intervalo em que o conflito acontece é muito curto. A IA propôs alargá-lo de propósito, e agora o teste falha se a
  trava for removida.
- **Validação só na entrada.** Os testes conferiam quantidade inválida apenas na entrada, então `saida(-1)` poderia
  aumentar o estoque sem que nenhum teste percebesse. Foi corrigido com testes nas quatro operações.
- **Defeito no código encontrado pela revisão.** Uma quantidade acima de 2⁶³−1 passa na validação e estoura no
  SQLite. Está registrado como `xfail` e na lista de melhorias do README.
- **A IA não executava o projeto.** O ambiente dela não tinha FastAPI nem SQLAlchemy, então toda execução real dos
  testes foi minha: 38 passaram na primeira versão e 112 passaram e 1 `xfailed` na versão final. A IA só validou a
  lógica dos testes contra um modelo em memória.
- **Exemplo no Swagger.** A primeira tentativa de mostrar um valor de exemplo no id do produto gerou um seletor
  indesejado. Apontei o problema e pedi um texto simples.

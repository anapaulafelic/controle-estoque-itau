# Uso de Inteligência Artificial

Este documento descreve como as ferramentas de Inteligência Artificial foram utilizadas como aceleradoras no desenvolvimento do case prático de Controle de Estoque, detalhando os modelos empregados, os principais prompts, os ganhos de produtividade, decisões técnicas ajustadas e limitações identificadas durante o processo.

---

## 1. Ferramentas e Modelos Utilizados

- **Claude** (Anthropic) - codificação
- **ChatGPT** (OpenAI) - estudo inicial de caso, regras de negócios, dúvidas técnicas e plano de desenvolvimento
- **Gemini** (Google) - validação e dúvidas técnicas

---

## 2. Onde a IA mais ajudou

- **Modelagem de Dados e Relacionamentos:** Apoio na interpretação dos requisitos de múltiplas reservas e bloqueios simultâneos por produto, contribuindo para a definição das entidades Produto, Reserva e Bloqueio, seus relacionamentos e identificações individuais. A discussão também abordou a liberação independente de cada registro.

- **Consistência e Concorrência:** Apoio na compreensão dos riscos de condições de corrida (race conditions) em operações simultâneas de estoque e das estratégias para preservar a consistência dos dados, considerando transações e mecanismos de controle de concorrência.

- **Regras de Negócio e Testes:** Apoio na identificação de cenários positivos, negativos e excepcionais, incluindo tentativas de movimentação acima da quantidade disponível, liberações duplicadas e operações inválidas. Também contribuiu para estruturar a estratégia de testes automatizados.

- **Organização da Arquitetura e Separação de Responsabilidades:** Discussão sobre a divisão entre rotas, serviços, modelos e schemas, buscando manter as regras de negócio centralizadas e independentes da camada de exposição da API e da persistência.

- **Avaliação de Alternativas e Alinhamento de Escopo:** Discussão sobre alternativas de arquitetura e tecnologias, considerando o prazo e os objetivos do case. A análise priorizou uma solução simples, organizada e testável, evitando complexidade desnecessária, como microsserviços e mensageria.

---

## 3. Principais Prompts Utilizados

### Prompt 1: Modelagem de Dados e Regras de Negócio

> _"Atue como engenheiro de software sênior especialista em Python. Analise o enunciado do case de Controle
> de Estoque, sem gerar código. Identifique entidades, relacionamentos, regras de negócio, validações e situações excepcionais.Proponha uma modelagem simples que permita múltiplas reservas e bloqueios por produto, com identificação individual e liberação independente. Explique as decisões.
> "_

### Prompt 2: Estratégia de Concorrência e Tratamento de Conflitos

> _"Atue como engenheiro de software sênior e analise as regras de negócio de uma API de Controle de Estoque. Identifique possíveis inconsistências em operações simultâneas, reservas, bloqueios e liberações.
> Avalie os riscos de concorrência e indique como preservar a consistência dos dados utilizando
> transações e recursos do banco de dados. Não gere código inicialmente. Explique os cenários, as alternativas e suas limitações."_

### Prompt 3: Estratégia e Isolamento de Testes

> _"Atue como engenheiro de QA em Python/pytest. Analise a implementação do estoque e crie cenários de teste para cenários positivos, negativos e excepcionais (liberações duplicadas, saldo insuficiente, quantidades inválidas). Utilize banco isolado em memória."_

### Prompt 4: Revisão Técnica e Qualidade de Código

> _"Faça uma revisão técnica como engenheiro de software sênior. Avalie organização, legibilidade, segurança, validações, tratamento de erros, consistência, transações e configuração por ambiente. Verifique credenciais expostas, segurança, duplicação e complexidade excessiva. Não reescreva tudo: liste problemas por prioridade, riscos e correções pontuais."_

---

## 4. Sugestões de IA Modificadas ou Rejeitadas

- **Camada de Repositório (Repository Pattern):** A IA sugeriu criar uma estrutura formal de repositórios (`Repository` + `Unit of Work`). **Decisão:** Optei por rejeitar essa abstração e acessar a sessão do SQLAlchemy diretamente na camada de serviço (`services.py`) para manter o desenvolvimento simples, legível e focado no limite de tempo de 3 horas.
- **Reserva e bloqueio unificados:** A IA juntou os dois itens com uma única forma de liberar. **Decisão:** Mantive as duas entidades separadas, dessa forma reservas pode receber o passo "efetivar" previsto como melhoria.
- **Nomes de funções e rotas:** A IA criou nomes próprios, fugindo do escopo do case. **Decisão:** Solicitei refatoração e adequação ao escopo aprovado (Entrada, Saída, Reservar, Bloquear, Liberar, Consultar).
- **Quantidade de testes:** A IA chegou a quase 200 testes. **Decisão:** Apesar de importantes e válidos para o projeto, aumentou a complexidade e implementou funcionalidades em um nível muito superior ao meu conhecimento e ao escopo do case. Pedi para manter cobertura para as principais funções solicitadas e para as relacionadas a segurança.
- **Código do produto:** A IA entendeu que aceitar qualquer texto neste campo era coerente.**Decisão:** Optei por restringir os caracteres por segurança, evitando códigos com espaços e caracteres maliciosos.

---

## 5. Erros, Limitações e Problemas Identificados

- **Desvio do enunciado.** A IA renomeou as rotas do case e uniu reserva e bloqueio na mesma função, sem eu pedir. Percebi ao revisar o Swagger e pedi a correção (ver seção 4).
- **Campo desnecessário no Swagger.** A primeira tentativa de mostrar um exemplo no id do produto criou um campo seletor sem valores. Troquei por um exemplo fixo e uma descrição no próprio campo.
- **Quantidade gigante gerava erro 500.** Um valor acima de 64 bits (2⁶³−1) passava na validação e estourava no banco. Defini o limite de 1.000.000 por operação, já que o case não define valor máximo.
- **Execução/avaliação dos testes:** A IA não executava o projeto, a menos que eu desse permissão de acesso e execução na minha máquina. Por segurança, preferi rodar os testes no terminal localmente e compartilhar com ela somente os resultados.

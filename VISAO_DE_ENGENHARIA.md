# Visão de engenharia: os 5 aspectos mais importantes

As quatro metas do case: confiabilidade, qualidade, eficiência e evolução.

## 1. Estoque sempre correto (confiabilidade)

**Por que importa:** O valor de um sistema de estoque é o número em que se pode confiar. Se o total deixar de ser igual a `disponível + reservada + bloqueada`, não há como garantir segurança e confiabilidade das transações.

**O que a solução faz hoje.**

- O produto guarda só o total. As outras quantidades são calculadas somando as reservas e os bloqueios ativos, então todos os números partem do mesmo lugar.
- A regra é conferida **antes** de alterações. Por isso, um pedido recusado não afeta dos demais números.
- Os dados são conferidos em três lugares: no formato (Pydantic), no serviço e na própria base de dados.

**Para produção:** Adotar a mesma regra no banco de dados escolhido(ver o aspecto 2).

## 2. Pedidos ao mesmo tempo sem conflito (confiabilidade)

**Por que importa:** O erro mais caro num estoque é prometer duas vezes a mesma unidade. O risco está no intervalo entre "ver quanto tem disponível" e "alterar": dois pedidos simultâneos podem ver 10 disponíveis e cada um reservar 8, por exemplo.

**O que a solução faz hoje:** Uma trava faz uma operação de cada vez conferir e alterar o estoque. Há um teste com 50 pedidos simultâneos disputando 30 unidades, e ele falha se a trava for removida.

**Para produção:** As travas em memória só funcionam para uma única instância/processo. Em um ambiente de produção, o controle de concorrência precisa ser centralizado, geralmente através de travas no próprio banco de dados ou da adoção de um serviço de mensageria/fila.

## 3. Testes orientados a comportamento e borda (qualidade)

**Por que importa:** O objetivo é manter a segurança contra regressões. Um conjunto de testes confiável blinda as regras de negócio, permitindo que o núcleo do sistema seja alterado sem risco de corromper a consistência do estoque.

**O que a solução faz hoje:** 122 casos, cada um com um banco vazio/limpo. Cobre cenários de sucesso, concorrência e garante a integridade do estado após operações inválidas. O arquivo [`TESTES.md`](TESTES.md) documenta defeitos intencionais para provar a eficácia das validações.

**Para produção:** Automatizar a rotina de testes para validar o código a cada nova alteração.

## 4. Desempenho em consultas (eficiência)

**Por que importa:** Consultar o saldo é a operação mais comum, mas somar o histórico todo a cada leitura é lento. Por outro lado, manter o saldo consolidado no produto otimiza a leitura, mas cria um gargalo de concorrência se muitas requisições tentarem atualizar a mesma linha simultaneamente.

**O que a solução faz hoje:** A listagem tem um limite estático (teto de 50 itens), assumindo a falta de filtros avançados como uma limitação registrada no README.

**Para produção:** Meu conhecimento prático sobre bancos de dados de altíssimo tráfego ainda está em desenvolvimento. Através de pesquisas e debates com a IA durante a construção deste case, entendi que a solução seguiria o caminho de filas e mensageria. A conclusão técnica é que, em um cenário de pico (ex: Black Friday), a arquitetura precisaria mudar: o controle dos saldos em tempo real migraria para um cache atômico em memória (como Redis) para suportar alta concorrência sem travas. O banco de dados relacional atuaria de forma assíncrona, apenas consolidando o histórico de movimentações (log de eventos).

## 5. Evolução e Rastreabilidade (Evolução)

**Por que importa:** Em um cenário real, toda variação numérica no estoque deve ser auditável para justificar perdas ou falhas operacionais. Além disso, a arquitetura deve suportar o crescimento do negócio (como a futura adição da etapa de "efetivação de reserva") sem risco de quebrar o que já está funcionando.

**O que a solução faz hoje:** Reserva e Bloqueio são separados, e as regras estão concentradas em um arquivo (`services.py`), o que facilita a criação de novos status e funções no futuro de forma isolada. Efetivar uma reserva seria um novo status e uma nova função, sem mexer no que já funciona. A ausência atual de logs de auditoria e rastreio de usuários foi mapeada nas limitações do README.

**Para produção:** Implementar histórico completo de movimentações (cada entrada, saída, reserva, bloqueio e liberação guardada de forma imutável), logs de auditoria e login com registro das ações de cada usuário.

Como complemento da pesquisa e dos debates com a IA, a sugestão para a arquitetura seria: Implementar o conceito de chaves de idempotência nas APIs, garantindo proteção contra requisições duplicadas (para que o sistema recuse a mesma operação caso o cliente clique duas vezes por conta de uma falha de rede). Além disso, para manter um controle seguro sobre as futuras mudanças na estrutura das tabelas à medida que o sistema cresce, a arquitetura exigiria a adoção de uma ferramenta de versionamento de banco de dados (como Alembic, Liquibase ou Flyway).

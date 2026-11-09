# Visão de engenharia: os 5 aspectos mais importantes

Em ordem de prioridade. Cada um está ligado a uma das quatro metas do case: confiabilidade, qualidade, eficiência
e evolução.

## 1. Estoque sempre correto (confiabilidade)

**Por que importa.** O valor de um sistema de estoque é o número em que se pode confiar. Se o total deixar de ser
igual a `disponível + reservada + bloqueada`, o resto não tem utilidade.

**O que a solução faz hoje.**
- O produto guarda só o total. As outras quantidades são calculadas somando as reservas e os bloqueios ativos, então
  todos os números nascem do mesmo lugar e não têm como se contradizer.
- A regra é conferida **antes** de alterar. Por isso, um pedido recusado não muda nada.
- Os dados são conferidos em três lugares: no formato (Pydantic), no serviço e no próprio banco.

**Para produção.** Deixar o banco de dados garantir a mesma regra (ver o aspecto 2).

## 2. Pedidos ao mesmo tempo sem conflito (confiabilidade)

**Por que importa.** O erro mais caro num estoque é prometer duas vezes a mesma unidade. O risco está no intervalo
entre "ver quanto tem disponível" e "alterar": dois pedidos simultâneos podem ver 10 disponíveis e cada um reservar 8.

**O que a solução faz hoje.** Uma trava faz uma operação de cada vez conferir e alterar o estoque. Há um teste com 50
pedidos simultâneos disputando 30 unidades, e ele falha se a trava for removida.

**Para produção.** A trava só vale para um processo. Com vários processos, a proteção precisa ficar no banco de dados
(por exemplo, no PostgreSQL, travando a linha do produto enquanto uma operação está em andamento).

## 3. Testes que provam as regras e conseguem falhar (qualidade)

**Por que importa.** A solução já passou por uma mudança grande (separar reserva e bloqueio). Sem testes, mexer em
algo central é arriscado. E qualidade não é ter muitos testes: é ter testes capazes de **perceber** um defeito.

**O que a solução faz hoje.** 113 casos, cada um com um banco novo. Eles cobrem o caminho normal, os erros, o que
acontece com o estoque depois de uma operação recusada, a liberação repetida e os pedidos simultâneos. O arquivo
[`TESTES.md`](TESTES.md) tem uma lista de defeitos para criar de propósito no código e conferir que algum teste falha.

**Para produção.** Rodar os testes automaticamente a cada alteração e repetir os de pedidos simultâneos com o banco
real.

## 4. Continuar rápido com muitos dados (eficiência)

**Por que importa.** Consultar um produto é a operação mais comum. Hoje o código soma todas as reservas e bloqueios
dele, então a consulta fica mais lenta quanto maior for o histórico.

**O que a solução faz hoje.** A listagem tem um teto de 50 itens, e o restante está registrado como limitação no README.

**Para produção.** Guardar as quantidades reservada e bloqueada já calculadas, atualizando-as junto com cada operação,
e buscar por páginas, com filtros, em produtos, reservas e bloqueios.

## 5. Evoluir e saber explicar cada número (evolução e rastreabilidade)

**Por que importa.** O próprio enunciado antecipa mudanças: a reserva vai ganhar o passo de efetivação, e novas regras
costumam aparecer. Além disso, num estoque é preciso poder explicar de onde veio cada número e quem fez cada operação.

**O que a solução faz hoje.** Reserva e Bloqueio são separados e usam os nomes do enunciado, e as regras ficam todas em
um só arquivo (`services.py`). Efetivar uma reserva seria um novo status e uma nova função, sem mexer no que já
funciona. Hoje **não** há logs nem registro de quem fez cada operação (está nas limitações do README).

**Para produção.** Histórico de movimentações (cada entrada, saída, reserva, bloqueio e liberação guardada para sempre),
logs e auditoria, login com registro das ações de cada usuário, proteção contra o mesmo pedido enviado duas vezes e
controle de mudanças da estrutura do banco.

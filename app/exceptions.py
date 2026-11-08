"""Erros de regra de negócio. O main.py traduz cada um em um código HTTP."""


class ErroDeDominio(Exception):
    """Base de todos os erros de regra de negócio."""


class QuantidadeInvalida(ErroDeDominio):
    def __init__(self, quantidade):
        super().__init__(f"Quantidade inválida: {quantidade!r}. Informe um inteiro maior que zero.")


class ProdutoIdInvalido(ErroDeDominio):
    def __init__(self):
        super().__init__(
            "Identificador de produto inválido. Use apenas letras, números, hífen e sublinhado "
            "(até 64 caracteres), sem espaços."
        )


class ProdutoNaoEncontrado(ErroDeDominio):
    def __init__(self, produto_id):
        super().__init__(f"Produto '{produto_id}' não encontrado.")


class ReservaNaoEncontrada(ErroDeDominio):
    def __init__(self, reserva_id):
        super().__init__(f"Reserva '{reserva_id}' não encontrada.")


class BloqueioNaoEncontrado(ErroDeDominio):
    def __init__(self, bloqueio_id):
        super().__init__(f"Bloqueio '{bloqueio_id}' não encontrado.")


class EstoqueInsuficiente(ErroDeDominio):
    def __init__(self, produto_id, solicitado, disponivel):
        super().__init__(
            f"Estoque insuficiente para o produto '{produto_id}': "
            f"solicitado {solicitado}, disponível {disponivel}."
        )


class ReservaJaLiberada(ErroDeDominio):
    def __init__(self, reserva_id):
        super().__init__(f"Reserva '{reserva_id}' já foi liberada.")


class BloqueioJaLiberado(ErroDeDominio):
    def __init__(self, bloqueio_id):
        super().__init__(f"Bloqueio '{bloqueio_id}' já foi liberado.")

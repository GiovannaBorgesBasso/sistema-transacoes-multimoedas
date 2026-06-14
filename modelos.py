from typing import NamedTuple


class Transacao(NamedTuple):
    """
    Representa uma transação financeira imutável.
    """
    id: str
    valor: float
    moeda: str
    data: str
    descricao: str = ""

#Por que NamedTuple?É imutável (não dá pra alterar os campos depois de criado), o que reflete a natureza de uma transação financeira. Além disso, é leve e fácil de usar, permitindo acesso aos campos por nome.
from typing import NamedTuple
#NamedTuple É imutável, o que reflete a natureza de uma transação financeira.


class Transacao(NamedTuple):
    """
    Representa uma transação financeira imutável.
    """
    id: str
    valor: float
    moeda: str
    data: str
    descricao: str = ""



class TransacaoConvertida(NamedTuple):
    """
    Representa uma transação após conversão para a moeda base (BRL).
    Imutável, com rastreabilidade da taxa aplicada.
    """
    id: str
    valor_original: float
    moeda_original: str
    valor_brl: float
    taxa_aplicada: float
    data: str
    descricao: str = ""
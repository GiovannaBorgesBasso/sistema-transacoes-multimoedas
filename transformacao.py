"""
Núcleo puro da pipeline: normalização, conversão e filtragem.

Todas as funções deste módulo são puras — não tocam I/O, não mutam a entrada e
produzem uma nova versão dos dados a cada transformação.
"""
from modelos import Transacao, TransacaoConvertida


def normalizar(t: Transacao) -> Transacao:
    """
    Padroniza os campos de uma transação: moeda em maiúsculas e descrição sem
    espaços nas bordas. Retorna uma nova Transacao (não muta a entrada).
    """
    return t._replace(
        moeda=t.moeda.strip().upper(),
        descricao=t.descricao.strip(),
    )


def converter(t: Transacao, taxas: dict) -> TransacaoConvertida | None:
    """
    Converte o valor da transação para BRL usando a taxa da sua moeda.
    Retorna uma TransacaoConvertida, ou None se não houver taxa para a moeda.
    """
    taxa = taxas.get(t.moeda)
    if taxa is None:
        return None
    return TransacaoConvertida(
        id=t.id,
        valor_original=t.valor,
        moeda_original=t.moeda,
        valor_brl=round(t.valor * taxa, 2),
        taxa_aplicada=taxa,
        data=t.data,
        descricao=t.descricao,
    )


def filtrar(transacoes, criterio):
    """
    Função de alta ordem: retorna a sublista das transações que satisfazem o
    predicado `criterio`. A lista de entrada permanece intacta.
    """
    return [t for t in transacoes if criterio(t)]


def valor_minimo(minimo):
    """Critério: mantém transações com valor_brl >= minimo."""
    return lambda t: t.valor_brl >= minimo


def por_moeda(moeda):
    """Critério: mantém transações cuja moeda de origem é `moeda`."""
    return lambda t: t.moeda_original == moeda


def e_(*criterios):
    """Combinador AND: passa se todos os critérios passam."""
    return lambda t: all(c(t) for c in criterios)


def ou_(*criterios):
    """Combinador OR: passa se algum critério passa."""
    return lambda t: any(c(t) for c in criterios)

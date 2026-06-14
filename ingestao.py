import json
from typing import List
from modelos import Transacao


def carregar_transacoes(caminho_arquivo: str) -> List[Transacao]:
    """
    Lê um arquivo JSON contendo transações brutas e retorna
    uma lista imutável de objetos Transacao.
    """
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        dados_brutos = json.load(arquivo)

    transacoes = [
        Transacao(
            id=item["id"],
            valor=item["valor"],
            moeda=item["moeda"],
            data=item["data"],
            descricao=item.get("descricao", "")
        )
        for item in dados_brutos
    ]

    return transacoes
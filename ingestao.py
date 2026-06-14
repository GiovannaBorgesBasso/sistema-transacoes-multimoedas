"""
Borda de I/O (leitura): carrega transações brutas e taxas de câmbio.

`carregar_taxas` é o único ponto que pode disparar rede, e apenas quando o cache
está ausente ou expirado. A função de fetch e o instante atual são injetáveis,
o que permite testar a lógica de cache sem tocar a rede.
"""
import json
from datetime import datetime, timedelta
from typing import List

from modelos import Transacao
from fetch_taxas import buscar_taxas

TTL_HORAS = 24


def carregar_transacoes(caminho_arquivo: str) -> List[Transacao]:
    """
    Lê um arquivo JSON contendo transações brutas e retorna uma lista de
    objetos Transacao. Transações malformadas (campo ausente ou valor não
    numérico) são descartadas com aviso, sem interromper o processamento.
    """
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        dados_brutos = json.load(arquivo)

    transacoes = []
    for item in dados_brutos:
        try:
            transacao = Transacao(
                id=str(item["id"]),
                valor=float(item["valor"]),
                moeda=item["moeda"],
                data=item["data"],
                descricao=item.get("descricao", ""),
            )
        except (KeyError, ValueError, TypeError) as erro:
            identificador = item.get("id", "<sem id>")
            print(f"[ingestao] aviso: transacao '{identificador}' descartada — {erro}")
            continue
        transacoes.append(transacao)

    return transacoes


def cache_valido(buscado_em: str, agora: str) -> bool:
    """Retorna True se o timestamp do cache está dentro do TTL de 24h."""
    instante = datetime.fromisoformat(buscado_em)
    referencia = datetime.fromisoformat(agora)
    return referencia - instante <= timedelta(hours=TTL_HORAS)


def carregar_taxas(caminho_arquivo: str, fetch=buscar_taxas, agora: str = None) -> dict:
    """
    Retorna o dicionário {moeda: taxa_brl}. Usa o cache em `caminho_arquivo` se
    existir e estiver dentro do TTL; caso contrário dispara `fetch` e regrava.
    Se o fetch falhar mas houver cache (mesmo velho), usa o cache com aviso; se
    não houver cache, propaga o erro.

    `fetch` e `agora` (ISO str) são injetáveis para permitir testes sem rede.
    """
    if agora is None:
        agora = datetime.now().isoformat(timespec="seconds")

    cache = None
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if "taxas" in dados and "buscado_em" in dados:
            cache = dados
    except (FileNotFoundError, json.JSONDecodeError):
        cache = None

    if cache and cache_valido(cache["buscado_em"], agora):
        return cache["taxas"]

    try:
        taxas = fetch()
    except Exception as erro:
        if cache:
            print(f"[ingestao] aviso: fetch falhou ({erro}); usando cache velho")
            return cache["taxas"]
        raise

    conteudo = {"buscado_em": agora, "taxas": taxas}
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
    return taxas

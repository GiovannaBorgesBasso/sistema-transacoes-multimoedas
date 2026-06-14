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

# adicionar aos imports existentes
from datetime import datetime, timedelta
import subprocess

TTL_HORAS = 24


def carregar_taxas(caminho_arquivo: str) -> dict:
    """
    Carrega taxas de câmbio com cache TTL de 24h.
    Se ausente ou expirado, executa fetch_taxas.py para atualizar.
    """
    cache = _ler_cache(caminho_arquivo)

    if cache is None or _cache_velho(cache):
        try:
            subprocess.run(["python", "fetch_taxas.py"], check=True)
            cache = _ler_cache(caminho_arquivo)
        except Exception:
            if cache is not None:
                print("Aviso: falha ao buscar taxas atualizadas, usando cache existente.")
            else:
                raise RuntimeError("Sem taxas disponíveis: API falhou e não há cache.")

    return cache["taxas"]


def _ler_cache(caminho_arquivo: str):
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if "taxas" in dados and "buscado_em" in dados:
            return dados
        return None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _cache_velho(cache: dict) -> bool:
    buscado_em = datetime.fromisoformat(cache["buscado_em"])
    return datetime.now() - buscado_em > timedelta(hours=TTL_HORAS)
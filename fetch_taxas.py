"""
Script standalone: busca taxas de câmbio (base BRL) numa API pública e grava
dados/taxas.json com timestamp. Também expõe `buscar_taxas`, reutilizada pela
borda de ingestão. Único ponto do projeto que toca a rede.
"""
import json
import urllib.request
from datetime import datetime

URL_API = "https://open.er-api.com/v6/latest/BRL"
CAMINHO_TAXAS = "dados/taxas.json"


def buscar_taxas() -> dict:
    """
    Busca taxas na API e retorna {moeda: taxa_para_brl}.

    A API retorna BRL->moeda (quanto vale 1 BRL em cada moeda); invertemos para
    moeda->BRL (quanto vale 1 unidade da moeda em BRL).
    """
    with urllib.request.urlopen(URL_API, timeout=10) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    rates = dados["rates"]
    return {moeda: round(1.0 / taxa, 4) for moeda, taxa in rates.items() if taxa}


def gravar_taxas(caminho: str = CAMINHO_TAXAS) -> None:
    """Busca as taxas e grava o cache com timestamp em `caminho`."""
    taxas = buscar_taxas()
    conteudo = {"buscado_em": datetime.now().isoformat(timespec="seconds"), "taxas": taxas}
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
    print(f"[fetch_taxas] {len(taxas)} taxas gravadas em {caminho}")


if __name__ == "__main__":
    gravar_taxas()

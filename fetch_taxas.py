import json
import urllib.request
from datetime import datetime

URL_API = "https://api.exchangerate-api.com/v4/latest/BRL"
CAMINHO_SAIDA = "dados/taxas.json"


def buscar_taxas() -> dict:
    """
    Busca taxas de câmbio reais e retorna no formato:
    {"buscado_em": ..., "taxas": {"USD": ..., "EUR": ...}}

    A API retorna quantos BRL valem em USD/EUR (ex: 1 BRL = 0.19 USD).
    Invertemos para obter quanto vale 1 USD/EUR em BRL.
    """
    with urllib.request.urlopen(URL_API) as resposta:
        dados = json.loads(resposta.read())

    rates = dados["rates"]
    taxas = {
        "USD": round(1 / rates["USD"], 4),
        "EUR": round(1 / rates["EUR"], 4),
    }

    return {
        "buscado_em": datetime.now().isoformat(),
        "taxas": taxas
    }


def salvar_taxas(caminho: str = CAMINHO_SAIDA):
    resultado = buscar_taxas()
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"Taxas salvas em {caminho}: {resultado['taxas']}")


if __name__ == "__main__":
    salvar_taxas()
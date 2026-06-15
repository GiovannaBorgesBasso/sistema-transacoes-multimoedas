"""Orquestrador da pipeline de processamento de transações multimoedas."""
from ingestao import carregar_transacoes, carregar_taxas
from transformacao import normalizar, converter, filtrar, valor_minimo
from saida import exportar_json, gerar_relatorio, imprimir_relatorio

CAMINHO_TRANSACOES = "dados/transacoes.json"
CAMINHO_TAXAS = "dados/taxas.json"
CAMINHO_SAIDA = "saida.json"
VALOR_MINIMO_BRL = 100.0


def main():
    # Ingestão (borda)
    brutas = carregar_transacoes(CAMINHO_TRANSACOES)
    taxas = carregar_taxas(CAMINHO_TAXAS)

    # Transformação (núcleo puro)
    normalizadas = [normalizar(t) for t in brutas]
    convertidas = [c for c in (converter(t, taxas) for t in normalizadas) if c is not None]
    relevantes = filtrar(convertidas, valor_minimo(VALOR_MINIMO_BRL))

    # Saída (borda)
    exportar_json(relevantes, CAMINHO_SAIDA)
    imprimir_relatorio(gerar_relatorio(relevantes))
    print(f"\n{len(relevantes)} transações exportadas para {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()

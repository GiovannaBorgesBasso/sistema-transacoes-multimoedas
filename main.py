"""Orquestrador da pipeline de processamento de transações multimoedas."""
from ingestao import carregar_transacoes, carregar_taxas
from transformacao import normalizar, converter, filtrar, valor_minimo, por_moeda, e_, nao_
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

    # Critério composto: câmbio relevante = acima do mínimo E moeda estrangeira.
    # BRL→BRL (taxa 1.0) não é conversão, então fica de fora do relatório de câmbio.
    cambio_relevante = e_(valor_minimo(VALOR_MINIMO_BRL), nao_(por_moeda("BRL")))
    relevantes = filtrar(convertidas, cambio_relevante)

    # Saída (borda)
    exportar_json(relevantes, CAMINHO_SAIDA)
    imprimir_relatorio(gerar_relatorio(relevantes))
    print(f"\n{len(relevantes)} transações exportadas para {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()

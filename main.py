from ingestao import carregar_transacoes, carregar_taxas


def main():
    transacoes = carregar_transacoes("dados/transacoes.json")
    print(f"{len(transacoes)} transações carregadas.")

    taxas = carregar_taxas("dados/taxas.json")
    print(f"Taxas: {taxas}")


if __name__ == "__main__":
    main()
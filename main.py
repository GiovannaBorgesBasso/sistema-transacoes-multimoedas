from ingestao import carregar_transacoes

transacoes = carregar_transacoes("dados/transacoes.json")
for t in transacoes:
    print(t)
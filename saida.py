"""Borda de saída: exporta transações convertidas e gera relatório consolidado."""
import json


def exportar_json(transacoes, caminho_arquivo: str) -> None:
    """Grava a lista de TransacaoConvertida como JSON."""
    dados = [t._asdict() for t in transacoes]
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def gerar_relatorio(transacoes) -> dict:
    """
    Consolida: total em BRL, média e, por moeda de origem, contagem e soma.
    Listas vazias produzem zeros, sem divisão por zero.
    """
    total = sum(t.valor_brl for t in transacoes)
    quantidade = len(transacoes)

    por_moeda = {}
    for t in transacoes:
        entrada = por_moeda.setdefault(t.moeda_original, {"contagem": 0, "soma_brl": 0.0})
        entrada["contagem"] += 1
        entrada["soma_brl"] = round(entrada["soma_brl"] + t.valor_brl, 2)

    return {
        "total_brl": round(total, 2),
        "media_brl": round(total / quantidade, 2) if quantidade else 0,
        "contagem": quantidade,
        "por_moeda": por_moeda,
    }


def imprimir_relatorio(relatorio: dict) -> None:
    """Exibe o relatório consolidado no terminal."""
    print("\n=== Relatório Consolidado ===")
    print(f"Transações: {relatorio['contagem']}")
    print(f"Total: R$ {relatorio['total_brl']:.2f}")
    print(f"Média: R$ {relatorio['media_brl']:.2f}")
    print("Por moeda de origem:")
    for moeda, d in relatorio["por_moeda"].items():
        print(f"  {moeda}: {d['contagem']} transações, R$ {d['soma_brl']:.2f}")

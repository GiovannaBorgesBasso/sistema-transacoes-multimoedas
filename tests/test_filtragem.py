from modelos import TransacaoConvertida
from transformacao import filtrar, valor_minimo, por_moeda, e_, ou_, nao_


def _tc(id, valor_brl, moeda):
    return TransacaoConvertida(
        id=id, valor_original=valor_brl, moeda_original=moeda,
        valor_brl=valor_brl, taxa_aplicada=1.0, data="2024-01-15",
    )


TXS = [_tc("1", 50.0, "USD"), _tc("2", 150.0, "EUR"), _tc("3", 300.0, "USD")]


def test_valor_minimo():
    r = filtrar(TXS, valor_minimo(100))
    assert {t.id for t in r} == {"2", "3"}


def test_por_moeda():
    r = filtrar(TXS, por_moeda("USD"))
    assert {t.id for t in r} == {"1", "3"}


def test_combinador_e():
    r = filtrar(TXS, e_(valor_minimo(100), por_moeda("USD")))
    assert {t.id for t in r} == {"3"}


def test_combinador_ou():
    r = filtrar(TXS, ou_(por_moeda("EUR"), valor_minimo(300)))
    assert {t.id for t in r} == {"2", "3"}


def test_combinador_nao():
    r = filtrar(TXS, nao_(por_moeda("USD")))
    assert {t.id for t in r} == {"2"}


def test_combinador_composto_e_nao():
    r = filtrar(TXS, e_(valor_minimo(100), nao_(por_moeda("USD"))))
    assert {t.id for t in r} == {"2"}


def test_filtrar_lista_vazia():
    assert filtrar([], valor_minimo(0)) == []


def test_filtrar_preserva_original():
    filtrar(TXS, valor_minimo(100))
    assert len(TXS) == 3  # entrada intacta

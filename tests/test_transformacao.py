from modelos import Transacao, TransacaoConvertida
from transformacao import normalizar, converter


# --- normalizar ---

def test_normalizar_moeda_para_maiusculas():
    t = Transacao(id="1", valor=10.0, moeda="usd", data="2024-01-15", descricao="x")
    r = normalizar(t)
    assert r.moeda == "USD"


def test_normalizar_trim_descricao():
    t = Transacao(id="1", valor=10.0, moeda="USD", data="2024-01-15", descricao="  pago  ")
    r = normalizar(t)
    assert r.descricao == "pago"


def test_normalizar_preserva_original():
    t = Transacao(id="1", valor=10.0, moeda="usd", data="2024-01-15")
    normalizar(t)
    assert t.moeda == "usd"  # original intacto (imutabilidade)


# --- converter ---

TAXAS = {"USD": 5.0, "EUR": 6.0, "BRL": 1.0}


def test_converter_calcula_valor_brl():
    t = Transacao(id="1", valor=10.0, moeda="USD", data="2024-01-15")
    r = converter(t, TAXAS)
    assert isinstance(r, TransacaoConvertida)
    assert r.valor_brl == 50.0
    assert r.taxa_aplicada == 5.0
    assert r.valor_original == 10.0
    assert r.moeda_original == "USD"


def test_converter_moeda_base_brl():
    t = Transacao(id="1", valor=42.0, moeda="BRL", data="2024-01-15")
    r = converter(t, TAXAS)
    assert r.valor_brl == 42.0


def test_converter_moeda_sem_taxa_retorna_none():
    t = Transacao(id="1", valor=10.0, moeda="JPY", data="2024-01-15")
    assert converter(t, TAXAS) is None

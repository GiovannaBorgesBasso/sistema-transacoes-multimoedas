import json

from modelos import TransacaoConvertida
from saida import exportar_json, gerar_relatorio


def _tc(id, valor_brl, moeda):
    return TransacaoConvertida(
        id=id, valor_original=valor_brl, moeda_original=moeda,
        valor_brl=valor_brl, taxa_aplicada=1.0, data="2024-01-15", descricao="x",
    )


TXS = [_tc("1", 100.0, "USD"), _tc("2", 200.0, "USD"), _tc("3", 300.0, "EUR")]


def test_exportar_json_grava_lista(tmp_path):
    caminho = str(tmp_path / "saida.json")
    exportar_json(TXS, caminho)
    dados = json.loads(open(caminho, encoding="utf-8").read())
    assert len(dados) == 3
    assert dados[0]["id"] == "1"
    assert dados[0]["valor_brl"] == 100.0


def test_relatorio_total_brl():
    r = gerar_relatorio(TXS)
    assert r["total_brl"] == 600.0


def test_relatorio_por_moeda():
    r = gerar_relatorio(TXS)
    assert r["por_moeda"]["USD"]["contagem"] == 2
    assert r["por_moeda"]["USD"]["soma_brl"] == 300.0
    assert r["por_moeda"]["EUR"]["contagem"] == 1


def test_relatorio_media():
    r = gerar_relatorio(TXS)
    assert r["media_brl"] == 200.0


def test_relatorio_vazio():
    r = gerar_relatorio([])
    assert r["total_brl"] == 0
    assert r["media_brl"] == 0
    assert r["por_moeda"] == {}

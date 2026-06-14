import json

import pytest

from ingestao import carregar_transacoes


def _escrever(tmp_path, dados):
    caminho = tmp_path / "t.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return str(caminho)


def test_carrega_transacoes_validas(tmp_path):
    caminho = _escrever(tmp_path, [
        {"id": "1", "valor": 10.0, "moeda": "USD", "data": "2024-01-15"},
    ])
    txs = carregar_transacoes(caminho)
    assert len(txs) == 1
    assert txs[0].id == "1"
    assert txs[0].descricao == ""


def test_descarta_malformada_campo_faltando(tmp_path, capsys):
    caminho = _escrever(tmp_path, [
        {"id": "1", "valor": 10.0, "moeda": "USD", "data": "2024-01-15"},
        {"id": "2", "valor": 20.0, "moeda": "EUR"},  # falta 'data'
    ])
    txs = carregar_transacoes(caminho)
    assert len(txs) == 1
    assert "2" in capsys.readouterr().out  # avisou sobre a descartada


def test_descarta_valor_nao_numerico(tmp_path):
    caminho = _escrever(tmp_path, [
        {"id": "1", "valor": "abc", "moeda": "USD", "data": "2024-01-15"},
    ])
    txs = carregar_transacoes(caminho)
    assert len(txs) == 0


def test_arquivo_ausente_erro_claro(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_transacoes(str(tmp_path / "nao_existe.json"))

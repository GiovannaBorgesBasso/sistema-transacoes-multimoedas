import json

from ingestao import carregar_taxas, cache_valido

AGORA = "2026-06-14T12:00:00"


def _gravar_cache(tmp_path, buscado_em, taxas):
    caminho = tmp_path / "taxas.json"
    caminho.write_text(
        json.dumps({"buscado_em": buscado_em, "taxas": taxas}), encoding="utf-8"
    )
    return str(caminho)


def test_cache_valido_dentro_do_ttl():
    assert cache_valido("2026-06-14T11:00:00", agora=AGORA) is True


def test_cache_invalido_acima_do_ttl():
    assert cache_valido("2026-06-13T11:00:00", agora=AGORA) is False


def test_usa_cache_quando_valido(tmp_path):
    caminho = _gravar_cache(tmp_path, "2026-06-14T11:00:00", {"USD": 5.0})

    def fetch_falso():
        raise AssertionError("nao deveria buscar quando cache valido")

    taxas = carregar_taxas(caminho, fetch=fetch_falso, agora=AGORA)
    assert taxas == {"USD": 5.0}


def test_busca_quando_cache_expirado(tmp_path):
    caminho = _gravar_cache(tmp_path, "2026-06-01T00:00:00", {"USD": 1.0})

    def fetch_falso():
        return {"USD": 9.9}

    taxas = carregar_taxas(caminho, fetch=fetch_falso, agora=AGORA)
    assert taxas == {"USD": 9.9}


def test_busca_quando_arquivo_ausente(tmp_path):
    caminho = str(tmp_path / "nao_existe.json")

    def fetch_falso():
        return {"EUR": 6.0}

    taxas = carregar_taxas(caminho, fetch=fetch_falso, agora=AGORA)
    assert taxas == {"EUR": 6.0}


def test_fallback_para_cache_velho_se_fetch_falha(tmp_path, capsys):
    caminho = _gravar_cache(tmp_path, "2026-06-01T00:00:00", {"USD": 1.0})

    def fetch_falho():
        raise ConnectionError("sem rede")

    taxas = carregar_taxas(caminho, fetch=fetch_falho, agora=AGORA)
    assert taxas == {"USD": 1.0}
    assert "aviso" in capsys.readouterr().out.lower()

# Pipeline Multimoedas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir a pipeline DOP de processamento de transações multimoedas — ingestão, normalização, conversão para BRL, filtragem componível e saída (JSON + relatório).

**Architecture:** Pipeline de funções puras sobre dados imutáveis (`NamedTuple`). I/O isolado nas bordas (`ingestao`, `saida`, `fetch_taxas`); núcleo (`transformacao`) 100% puro. Taxas de câmbio via cache com TTL de 24h.

**Tech Stack:** Python 3.13, pytest, `urllib` (stdlib, para fetch da API).

**Spec:** `docs/superpowers/specs/2026-06-14-multicoin-pipeline-design.md`

---

## Trabalho já existente (Giovanna)

`ingestao.py` já contém `carregar_transacoes` (commit `6232d3c`). Estado:
- **Reaproveitar:** a função lê JSON e mapeia para `Transacao` corretamente, com `.get` para `descricao`. Mantida como base.
- **Alterar (Task 4):** adicionar validação de borda — hoje um campo ausente gera `KeyError` cru; a spec pede descartar transações malformadas com aviso.
- **Completar (Task 5):** o módulo ainda não tem `carregar_taxas` (cache TTL).

`dados/transacoes.json` já populado com 5 transações de exemplo (USD, EUR, BRL). Reaproveitado nos testes de integração e na demo.

## Estrutura de Arquivos

| Arquivo | Responsabilidade | Status |
|---|---|---|
| `modelos.py` | Tipos imutáveis `Transacao`, `TransacaoConvertida` | Estender (Task 2) |
| `ingestao.py` | Borda leitura: `carregar_transacoes` (+validação), `carregar_taxas` (cache) | Estender (Task 4, 5) |
| `transformacao.py` | Núcleo puro: `normalizar`, `converter`, `filtrar`, critérios | Criar (Task 3, 6, 7) |
| `saida.py` | Borda escrita: `exportar_json`, `gerar_relatorio`, `imprimir_relatorio` | Criar (Task 8) |
| `fetch_taxas.py` | Script standalone: busca API, grava `taxas.json` com timestamp | Criar (Task 5) |
| `main.py` | Orquestrador da pipeline | Criar (Task 9) |
| `tests/` | Testes pytest das funções puras e bordas | Criar (Tasks 1, 3, 4, 6, 7, 8) |

---

## Task 1: Setup do ambiente de testes

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `conftest.py`

- [ ] **Step 1: Criar `requirements.txt`**

```
pytest>=8.0
```

- [ ] **Step 2: Instalar**

Run: `python3 -m pip install -r requirements.txt`
Expected: pytest instalado com sucesso.

- [ ] **Step 3: Criar `tests/__init__.py` (vazio) e `conftest.py` na raiz**

`conftest.py` garante que os módulos da raiz sejam importáveis nos testes:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 4: Verificar pytest roda**

Run: `python3 -m pytest -q`
Expected: "no tests ran" (sem erro de coleta).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py conftest.py
git commit -m "Configura ambiente de testes com pytest"
```

---

## Task 2: Estender modelos com TransacaoConvertida

**Files:**
- Modify: `modelos.py`

- [ ] **Step 1: Adicionar `TransacaoConvertida` ao `modelos.py`**

Manter `Transacao` como está. Adicionar abaixo:

```python
class TransacaoConvertida(NamedTuple):
    """
    Transação após conversão para a moeda base (BRL).
    Gerada pela etapa de conversão; carrega a taxa aplicada para rastreabilidade.
    """
    id: str
    valor_original: float
    moeda_original: str
    valor_brl: float
    taxa_aplicada: float
    data: str
    descricao: str = ""
```

- [ ] **Step 2: Verificar import**

Run: `python3 -c "from modelos import Transacao, TransacaoConvertida; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add modelos.py
git commit -m "Adiciona tipo TransacaoConvertida ao modelo de dados"
```

---

## Task 3: Normalização (núcleo puro)

**Files:**
- Create: `transformacao.py`
- Test: `tests/test_transformacao.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
from modelos import Transacao
from transformacao import normalizar


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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_transformacao.py -v`
Expected: FAIL — "No module named 'transformacao'".

- [ ] **Step 3: Implementação mínima**

```python
from modelos import Transacao


def normalizar(t: Transacao) -> Transacao:
    """
    Padroniza os campos de uma transação: moeda em maiúsculas,
    descrição sem espaços nas bordas. Retorna nova Transacao (não muta a entrada).
    """
    return t._replace(
        moeda=t.moeda.strip().upper(),
        descricao=t.descricao.strip(),
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tests/test_transformacao.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add transformacao.py tests/test_transformacao.py
git commit -m "Adiciona normalizacao de transacoes"
```

---

## Task 4: Validação na ingestão (alterar trabalho da Giovanna)

**Files:**
- Modify: `ingestao.py`
- Test: `tests/test_ingestao.py`

A função `carregar_transacoes` da Giovanna é mantida, mas passa a descartar
transações malformadas com aviso em vez de quebrar com `KeyError`.

- [ ] **Step 1: Escrever o teste que falha**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_ingestao.py -v`
Expected: FAIL — `test_descarta_malformada_campo_faltando` quebra com `KeyError` (sem tratamento).

- [ ] **Step 3: Substituir o corpo de `carregar_transacoes` em `ingestao.py`**

Manter os imports existentes. Substituir a list comprehension por um laço que valida:

```python
import json
from typing import List
from modelos import Transacao


def carregar_transacoes(caminho_arquivo: str) -> List[Transacao]:
    """
    Lê um arquivo JSON contendo transações brutas e retorna uma lista de
    objetos Transacao. Transações malformadas são descartadas com aviso.
    """
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        dados_brutos = json.load(arquivo)

    transacoes = []
    for item in dados_brutos:
        try:
            transacao = Transacao(
                id=str(item["id"]),
                valor=float(item["valor"]),
                moeda=item["moeda"],
                data=item["data"],
                descricao=item.get("descricao", ""),
            )
        except (KeyError, ValueError, TypeError) as erro:
            identificador = item.get("id", "<sem id>")
            print(f"[ingestao] aviso: transacao '{identificador}' descartada — {erro}")
            continue
        transacoes.append(transacao)

    return transacoes
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tests/test_ingestao.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add ingestao.py tests/test_ingestao.py
git commit -m "Adiciona validacao de transacoes malformadas na ingestao"
```

---

## Task 5: Fetch de taxas + cache com TTL

**Files:**
- Create: `fetch_taxas.py`
- Modify: `ingestao.py` (adiciona `carregar_taxas`)
- Test: `tests/test_taxas.py`

A API real é tocada apenas por `fetch_taxas`. A função `carregar_taxas` (borda)
decide se usa o cache ou dispara o fetch. Para manter os testes sem rede, `carregar_taxas`
recebe a função de fetch por injeção de dependência (default = fetch real).

- [ ] **Step 1: Escrever o teste que falha**

```python
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
    # buscado 1h antes de AGORA -> válido
    assert cache_valido("2026-06-14T11:00:00", agora=AGORA) is True


def test_cache_invalido_acima_do_ttl():
    # buscado 25h antes -> expirado
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_taxas.py -v`
Expected: FAIL — não há `carregar_taxas`/`cache_valido` em `ingestao`.

- [ ] **Step 3: Criar `fetch_taxas.py`**

```python
"""
Script standalone: busca taxas de câmbio (base BRL) numa API pública e grava
dados/taxas.json com timestamp. Também expõe `buscar_taxas` para reuso pela
borda de ingestão. Único ponto do projeto que toca a rede.
"""
import json
import urllib.request
from datetime import datetime

URL_API = "https://open.er-api.com/v6/latest/BRL"
CAMINHO_TAXAS = "dados/taxas.json"


def buscar_taxas() -> dict:
    """
    Busca taxas na API e retorna {moeda: taxa_para_brl}.
    A API retorna BRL->moeda; invertemos para moeda->BRL (1 / taxa).
    """
    with urllib.request.urlopen(URL_API, timeout=10) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    rates = dados["rates"]
    return {moeda: 1.0 / taxa for moeda, taxa in rates.items() if taxa}


def gravar_taxas(caminho: str = CAMINHO_TAXAS) -> None:
    taxas = buscar_taxas()
    conteudo = {"buscado_em": datetime.now().isoformat(timespec="seconds"), "taxas": taxas}
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
    print(f"[fetch_taxas] {len(taxas)} taxas gravadas em {caminho}")


if __name__ == "__main__":
    gravar_taxas()
```

- [ ] **Step 4: Adicionar `cache_valido` e `carregar_taxas` ao `ingestao.py`**

Adicionar ao topo dos imports: `from datetime import datetime, timedelta` e
`from fetch_taxas import buscar_taxas`. Adicionar as funções:

```python
TTL_HORAS = 24


def cache_valido(buscado_em: str, agora: str) -> bool:
    """Retorna True se o timestamp do cache está dentro do TTL de 24h."""
    instante = datetime.fromisoformat(buscado_em)
    referencia = datetime.fromisoformat(agora)
    return referencia - instante <= timedelta(hours=TTL_HORAS)


def carregar_taxas(caminho_arquivo: str, fetch=buscar_taxas, agora: str = None) -> dict:
    """
    Retorna o dicionário {moeda: taxa_brl}. Usa o cache em `caminho_arquivo` se
    existir e estiver dentro do TTL; caso contrário dispara `fetch` e regrava.
    Se o fetch falhar mas houver cache (mesmo velho), usa o cache com aviso.
    `agora` (ISO str) é injetável para testes; default = momento atual.
    """
    if agora is None:
        agora = datetime.now().isoformat(timespec="seconds")

    cache = None
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            cache = json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = None

    if cache and cache_valido(cache["buscado_em"], agora):
        return cache["taxas"]

    try:
        taxas = fetch()
    except Exception as erro:
        if cache:
            print(f"[ingestao] aviso: fetch falhou ({erro}); usando cache velho")
            return cache["taxas"]
        raise

    conteudo = {"buscado_em": agora, "taxas": taxas}
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
    return taxas
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python3 -m pytest tests/test_taxas.py -v`
Expected: PASS (6 testes).

- [ ] **Step 6: Commit**

```bash
git add fetch_taxas.py ingestao.py tests/test_taxas.py
git commit -m "Adiciona fetch de taxas e cache com TTL de 24h"
```

---

## Task 6: Conversão para BRL (núcleo puro)

**Files:**
- Modify: `transformacao.py`
- Test: `tests/test_transformacao.py`

- [ ] **Step 1: Adicionar testes que falham**

```python
from modelos import Transacao, TransacaoConvertida
from transformacao import converter

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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_transformacao.py -k converter -v`
Expected: FAIL — `converter` não existe.

- [ ] **Step 3: Implementação**

Adicionar a `transformacao.py` (importar `TransacaoConvertida` no topo):

```python
from modelos import Transacao, TransacaoConvertida


def converter(t: Transacao, taxas: dict) -> TransacaoConvertida | None:
    """
    Converte o valor da transação para BRL usando a taxa da sua moeda.
    Retorna TransacaoConvertida, ou None se não houver taxa para a moeda.
    """
    taxa = taxas.get(t.moeda)
    if taxa is None:
        return None
    return TransacaoConvertida(
        id=t.id,
        valor_original=t.valor,
        moeda_original=t.moeda,
        valor_brl=round(t.valor * taxa, 2),
        taxa_aplicada=taxa,
        data=t.data,
        descricao=t.descricao,
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tests/test_transformacao.py -k converter -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add transformacao.py tests/test_transformacao.py
git commit -m "Adiciona conversao de transacoes para BRL"
```

---

## Task 7: Filtragem componível (núcleo puro)

**Files:**
- Modify: `transformacao.py`
- Test: `tests/test_filtragem.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
from modelos import TransacaoConvertida
from transformacao import filtrar, valor_minimo, por_moeda, e_, ou_


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


def test_filtrar_lista_vazia():
    assert filtrar([], valor_minimo(0)) == []


def test_filtrar_preserva_original():
    filtrar(TXS, valor_minimo(100))
    assert len(TXS) == 3  # entrada intacta
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_filtragem.py -v`
Expected: FAIL — `filtrar`/critérios não existem.

- [ ] **Step 3: Implementação**

Adicionar a `transformacao.py`:

```python
def filtrar(transacoes, criterio):
    """Função de alta ordem: retorna as transações que satisfazem o predicado `criterio`."""
    return [t for t in transacoes if criterio(t)]


def valor_minimo(minimo):
    """Critério: valor_brl >= minimo."""
    return lambda t: t.valor_brl >= minimo


def por_moeda(moeda):
    """Critério: moeda_original == moeda."""
    return lambda t: t.moeda_original == moeda


def e_(*criterios):
    """Combinador AND: passa se todos os critérios passam."""
    return lambda t: all(c(t) for c in criterios)


def ou_(*criterios):
    """Combinador OR: passa se algum critério passa."""
    return lambda t: any(c(t) for c in criterios)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tests/test_filtragem.py -v`
Expected: PASS (6 testes).

- [ ] **Step 5: Commit**

```bash
git add transformacao.py tests/test_filtragem.py
git commit -m "Adiciona filtragem componivel com criterios e combinadores"
```

---

## Task 8: Saída — JSON e relatório

**Files:**
- Create: `saida.py`
- Test: `tests/test_saida.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python3 -m pytest tests/test_saida.py -v`
Expected: FAIL — não há módulo `saida`.

- [ ] **Step 3: Implementação**

```python
"""Borda de saída: exporta transações convertidas e gera relatório consolidado."""
import json


def exportar_json(transacoes, caminho_arquivo: str) -> None:
    """Grava a lista de TransacaoConvertida como JSON."""
    dados = [t._asdict() for t in transacoes]
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def gerar_relatorio(transacoes) -> dict:
    """
    Consolida: total em BRL, média, e por moeda de origem (contagem e soma).
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python3 -m pytest tests/test_saida.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commit**

```bash
git add saida.py tests/test_saida.py
git commit -m "Adiciona exportacao JSON e relatorio consolidado"
```

---

## Task 9: Orquestração (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implementar a pipeline em `main.py`**

```python
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
```

- [ ] **Step 2: Rodar a pipeline ponta a ponta**

Run: `python3 main.py`
Expected: relatório impresso no terminal e `saida.json` gravado. (A primeira execução busca taxas na API; execuções seguintes usam o cache.)

- [ ] **Step 3: Verificar a saída**

Run: `python3 -c "import json; d=json.load(open('saida.json')); print(len(d), 'transacoes')"`
Expected: número de transações ≥ 100 BRL (das 5 de exemplo: 001, 003, 005 em USD/EUR ficam; 002 e 004 dependem da taxa).

- [ ] **Step 4: Rodar a suíte completa**

Run: `python3 -m pytest -v`
Expected: todos os testes PASS.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "Adiciona orquestrador da pipeline (main)"
```

---

## Task 10: README

**Files:**
- Modify: `readme.md`

- [ ] **Step 1: Escrever o `readme.md`**

```markdown
# Sistema de Processamento de Transações Multimoedas

Pipeline em Python (paradigma orientado a dados) que ingere transações em várias
moedas, converte para BRL, filtra e gera saída estruturada.

## Estrutura
- `modelos.py` — tipos imutáveis (`Transacao`, `TransacaoConvertida`)
- `ingestao.py` — leitura de transações e taxas (cache TTL 24h)
- `transformacao.py` — núcleo puro: normalizar, converter, filtrar
- `saida.py` — exportação JSON e relatório
- `fetch_taxas.py` — busca taxas na API (standalone)
- `main.py` — orquestra a pipeline

## Uso
```bash
python3 -m pip install -r requirements.txt
python3 main.py          # roda a pipeline (busca taxas se cache vazio/velho)
python3 fetch_taxas.py   # atualiza taxas manualmente (opcional)
python3 -m pytest        # testes
```
```

- [ ] **Step 2: Commit**

```bash
git add readme.md
git commit -m "Adiciona README do projeto"
```

---

## Notas de implementação

- **TDD obrigatório:** escrever o teste, vê-lo falhar, implementar, vê-lo passar. Não pular o passo de ver falhar.
- **Imutabilidade:** o núcleo nunca muta a entrada — usa `_replace`/novos objetos. Há testes que verificam isso (Task 3, 7).
- **Sem rede nos testes:** `carregar_taxas` recebe `fetch` e `agora` por injeção; testes sempre passam fakes.
- **Reaproveitamento do trabalho da Giovanna:** `carregar_transacoes` (corpo alterado na Task 4) e `dados/transacoes.json` (usado na demo da Task 9).

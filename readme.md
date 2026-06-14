# Sistema de Processamento de Transações Multimoedas

Projeto final de **Linguagens e Paradigmas de Programação (LPP)**.

**Equipe:** Giovanna Borges Basso · Júlia Santos Coité · Milena Oliveira · Clara Batista
**Paradigma:** Programação Orientada a Dados (DOP) · **Linguagem:** Python

---

## O que é

Uma pipeline que recebe transações financeiras em moedas diferentes, converte tudo
para BRL e devolve um conjunto filtrado e um relatório consolidado. O objetivo do
projeto é menos "fazer câmbio" e mais **demonstrar o paradigma orientado a dados** num
caso real: dados imutáveis fluindo por funções puras.

## Por que orientado a dados

A ideia central do DOP é **separar dados de lógica**. Os dados são estruturas imutáveis
(`NamedTuple`); a lógica são funções puras que recebem dados e devolvem *novos* dados,
sem nunca alterar a entrada. Isso nos dá três coisas que guiaram todo o design:

- **Imutabilidade** — cada etapa produz uma nova versão; a anterior continua intacta.
- **Previsibilidade** — função pura: mesma entrada, mesma saída, sem efeito colateral.
- **Testabilidade** — sem estado escondido nem I/O no meio, testar é só passar um valor
  e conferir o retorno (daí os 27 testes rodarem sem rede nem mocks).

## Arquitetura: núcleo puro, efeitos nas bordas

O princípio que organiza o código todo:

```
fetch_taxas.py  (offline, única parte que toca a rede)  ──►  dados/taxas.json
                                                                  │
dados/transacoes.json ─►  ingestao  ─►  transformacao  ─►  saida  ─►  saida.json + relatório
                          (borda I/O)    (núcleo puro)     (borda I/O)
                          main.py orquestra ──────────────────────►
```

Rede e disco vivem **só nas pontas** (`ingestao`, `saida`, `fetch_taxas`). O miolo
(`transformacao`) é 100% puro. É essa fronteira que mantém a lógica de negócio
determinística e fácil de testar — o resto do design é consequência dela.

## O fluxo, ponta a ponta

1. **Ingestão** (`ingestao.carregar_transacoes`) lê o JSON bruto e monta `Transacao`.
   Transação malformada não derruba o processo: é descartada com aviso.
2. **Taxas** (`ingestao.carregar_taxas`) entrega `{moeda: taxa}`. Usa cache local; só
   busca na rede se o cache estiver ausente ou velho (ver *Decisões* abaixo).
3. **Normalização** (`transformacao.normalizar`) padroniza campos (moeda em maiúsculas,
   descrição sem espaços) → nova `Transacao`.
4. **Conversão** (`transformacao.converter`) aplica a taxa → `TransacaoConvertida`, que
   carrega o valor em BRL *e* a taxa usada (rastreabilidade). Moeda sem taxa é descartada.
5. **Filtragem** (`transformacao.filtrar`) seleciona o que importa via um critério.
6. **Saída** (`saida`) grava `saida.json` e imprime o relatório consolidado.

`main.py` é só a costura desses passos — leia-o primeiro para ver a pipeline inteira de
relance.

## Decisões de design (o "porquê")

- **Dois tipos de dado, não um.** `Transacao` (bruta) e `TransacaoConvertida` (pós-câmbio)
  são tipos distintos. Isso evita o estado ambíguo de "meio convertido" e faz cada etapa
  declarar o que produz. A conversão é uma transformação → gera um tipo novo.

- **Câmbio com cache + TTL de 24h.** Bater na API a cada execução traria latência e
  dependência de rede; exigir dois comandos manuais seria frágil. A solução: a borda lê o
  cache e só dispara a rede se ele estiver vazio ou com mais de 24h (câmbio é dado diário).
  Para testar isso sem rede, `carregar_taxas` recebe a função de fetch e o "agora" por
  injeção — os testes passam fakes.

- **Filtragem componível por funções de alta ordem.** `filtrar` recebe um *critério*
  (uma função). Em cima disso há blocos pequenos — `valor_minimo`, `por_moeda` — e
  combinadores — `e_`, `ou_` — que se compõem sem código novo:

  ```python
  filtrar(txs, e_(valor_minimo(100), por_moeda("USD")))   # "USD acima de 100 BRL"
  ```

  É aqui que o paradigma aparece mais claro: funções que recebem **e** retornam funções.

> Fundamentação completa de cada decisão em
> [`docs/superpowers/specs/2026-06-14-multicoin-pipeline-design.md`](docs/superpowers/specs/2026-06-14-multicoin-pipeline-design.md).

## Estrutura

```
main.py            # orquestra a pipeline (comece por aqui)
modelos.py         # Transacao e TransacaoConvertida (imutáveis)
ingestao.py        # borda de leitura: transações + taxas (cache TTL)
transformacao.py   # núcleo puro: normalizar, converter, filtrar
saida.py           # borda de escrita: JSON + relatório
fetch_taxas.py     # busca taxas reais na API (standalone)
dados/             # transacoes.json (entrada), taxas.json (cache)
tests/             # 27 testes — todos sem rede
docs/              # spec e plano de implementação
```

## Como executar

```bash
python3 -m pip install -r requirements.txt
python3 main.py          # roda a pipeline (busca taxas se o cache estiver vazio/velho)
python3 fetch_taxas.py   # atualiza as taxas manualmente (opcional)
python3 -m pytest        # roda os testes
```

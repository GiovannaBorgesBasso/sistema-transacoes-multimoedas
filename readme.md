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
  e conferir o retorno (daí os 29 testes rodarem sem rede nem mocks).

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
  combinadores — `e_`, `ou_`, `nao_` — que se compõem sem código novo. É exatamente
  o que `main.py` faz para montar a regra do relatório:

  ```python
  # câmbio relevante = acima do mínimo E moeda estrangeira (BRL→BRL não é conversão)
  cambio_relevante = e_(valor_minimo(100), nao_(por_moeda("BRL")))
  filtrar(convertidas, cambio_relevante)
  ```

  É aqui que o paradigma aparece mais claro: funções que recebem **e** retornam funções.
  A regra de negócio vira uma expressão legível, sem `if` espalhado pela pipeline.

## Estrutura

```
main.py            # orquestra a pipeline (comece por aqui)
modelos.py         # Transacao e TransacaoConvertida (imutáveis)
ingestao.py        # borda de leitura: transações + taxas (cache TTL)
transformacao.py   # núcleo puro: normalizar, converter, filtrar
saida.py           # borda de escrita: JSON + relatório
fetch_taxas.py     # busca taxas reais na API (standalone)
dados/             # transacoes.json (entrada), taxas.json (cache)
tests/             # 29 testes — todos sem rede
```

## Como executar

Requer **Python 3.10+** (usa o operador `|` em anotações de tipo). A pipeline em si
roda só com a biblioteca padrão; `requirements.txt` (`pytest`) é necessário apenas
para os testes.

```bash
python3 -m pip install -r requirements.txt
python3 main.py          # roda a pipeline (busca taxas se o cache estiver vazio/velho)
python3 fetch_taxas.py   # atualiza as taxas manualmente (opcional)
python3 -m pytest        # roda os testes
```

## Dados de exemplo

`dados/transacoes.json` traz ~15 transações em **seis moedas** — USD, EUR, GBP,
JPY, ARS e BRL — com valores calibrados pelas taxas reais. Além das transações
normais, o fixture inclui casos de borda de propósito, para mostrar que cada
etapa da pipeline trata o dado "sujo" sem derrubar o processo:

- **valor abaixo do mínimo** (R$100) → convertido, mas cortado na *filtragem*;
- **transação malformada** (valor não numérico) → descartada na *ingestão* com aviso;
- **moeda sem taxa** (`XYZ`) → descartada na *conversão*;
- **transações em BRL** → fora do relatório pelo critério de câmbio (`nao_(por_moeda("BRL"))`).

Das 15 entradas, 9 chegam ao relatório consolidado:

```
=== Relatório Consolidado ===
Transações: 9
Total: R$ 17143.21
Média: R$ 1904.80
Por moeda de origem:
  USD: 2 transações, R$ 2389.10
  EUR: 2 transações, R$ 7592.61
  GBP: 1 transações, R$ 1363.90
  JPY: 2 transações, R$ 2472.60
  ARS: 2 transações, R$ 3325.00
```

Os totais variam conforme a cotação do dia (taxas reais via API).

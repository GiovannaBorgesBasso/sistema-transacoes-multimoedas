# Sistema de Processamento de Transações Multimoedas

Projeto final da disciplina de Linguagens e Paradigmas de Programação (LPP).

**Equipe**: Giovanna Borges Basso, Júlia Santos Coité, Milena Oliveira, Clara Batista
**Paradigma**: Programação Orientada a Dados (DOP)
**Linguagem**: Python

## Visão Geral

Sistema que realiza ingestão, transformação e padronização de transações financeiras em múltiplas moedas, convertendo-as para BRL (moeda base) e gerando uma saída estruturada (JSON + relatório).

O sistema é estruturado como uma pipeline: dados imutáveis fluem por funções puras, onde cada etapa produz uma nova versão dos dados sem alterar a anterior.

## Arquitetura

fetch_taxas.py (offline, toca rede) ──► dados/taxas.json
│
dados/transacoes.json ─► ingestao ─► transformacao ─► saida ─► saida.json + relatório
(borda I/O)  (núcleo puro)    (borda I/O)
main.py orquestra ───────────────────────────────────►

Detalhes completos do design em `docs/superpowers/specs/2026-06-14-multicoin-pipeline-design.md`.

## Estrutura do Projeto

TrabalhoFinal_LPP/
├── main.py              # orquestra a pipeline
├── modelos.py           # Transacao e TransacaoConvertida (imutáveis)
├── ingestao.py          # leitura de transações e taxas (com cache TTL)
├── transformacao.py     # normalização, conversão e filtragem (núcleo puro)
├── saida.py             # exportação JSON e relatório
├── fetch_taxas.py        # busca taxas de câmbio reais
├── dados/
│   ├── transacoes.json  # transações de entrada
│   └── taxas.json       # cache de taxas de câmbio
└── docs/                 # especificação detalhada

## Como Executar

```bash
python3 -m pip install -r requirements.txt
python3 main.py          # roda a pipeline (busca taxas se o cache estiver vazio/velho)
python3 fetch_taxas.py   # atualiza as taxas manualmente (opcional)
python3 -m pytest        # roda os testes
```

## Status

- [x] Ingestão de transações (com validação de malformadas)
- [x] Carregamento de taxas com cache TTL (24h)
- [x] Normalização
- [x] Conversão para BRL
- [x] Filtragem componível (critérios + combinadores)
- [x] Saída (JSON + relatório)
- [x] Testes (27 passando)
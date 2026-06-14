# Spec — Sistema de Processamento de Transações Multimoedas

**Data:** 2026-06-14
**Projeto:** Seminário 1 (Projeto Final)
**Equipe:** Giovanna Borges Basso, Júlia Santos Coité, Milena Oliveira, Clara Batista
**Paradigma:** Programação Orientada a Dados (DOP)
**Linguagem:** Python

---

## 1. Visão Geral

Microaplicação que realiza ingestão, transformação e padronização de transações
financeiras em múltiplas moedas, convertendo-as para uma moeda base (BRL) e gerando
saída estruturada (JSON + relatório consolidado).

O sistema é estruturado como uma **pipeline de processamento de dados**: dados imutáveis
fluem por uma sequência de funções puras. Cada etapa produz uma nova versão dos dados,
mantendo as versões anteriores intactas.

## 2. Princípio Arquitetural

> **Núcleo puro, efeitos colaterais nas bordas.**

Rede e disco (I/O) ficam isolados nas pontas da pipeline. O miolo de transformação é
composto exclusivamente por funções puras — entrada determina saída, sem efeitos
colaterais, sem estado mutável.

```
fetch_taxas.py (offline, toca rede) ──► dados/taxas.json
                                              │
dados/transacoes.json ─► ingestao ─► transformacao ─► saida ─► saida.json + relatório
                         (borda I/O)  (núcleo puro)    (borda I/O)
        main.py orquestra ───────────────────────────────────►
```

**Fundamentação:** o paradigma DOP prioriza imutabilidade, redução de efeitos colaterais
e testabilidade. Concentrar I/O nas bordas mantém o núcleo (`transformacao`) 100% puro —
testável sem mocks de rede/disco — e torna a lógica de negócio determinística. Essa é a
expressão concreta dos três pilares do paradigma citados no seminário.

## 3. Fluxo de Dados

```
JSON bruto
  └─ ingestao.carregar_transacoes → list[Transacao]
       └─ map normalizar           → list[Transacao]            (campos padronizados)
            └─ carregar_taxas (borda: cache TTL / fetch)        → dict[str, float]
                 └─ map converter   → list[TransacaoConvertida] (valor BRL + taxa)
                      └─ filtrar(criterio) → list[TransacaoConvertida]
                           ├─ saida.exportar_json → saida.json
                           └─ saida.gerar_relatorio + imprimir
```

Cada seta produz uma **nova lista imutável**; a entrada permanece intacta. Isso
materializa o requisito do seminário: "cada transformação gera uma nova versão dos dados,
mantendo os dados originais imutáveis".

## 4. Modelo de Dados

Dois tipos imutáveis (`NamedTuple`), um por estágio do ciclo de vida do dado.

```python
class Transacao(NamedTuple):          # bruta / normalizada
    id: str
    valor: float
    moeda: str
    data: str
    descricao: str = ""

class TransacaoConvertida(NamedTuple): # pós-conversão
    id: str
    valor_original: float
    moeda_original: str
    valor_brl: float          # valor convertido para a moeda base
    taxa_aplicada: float      # rastreabilidade da taxa usada
    data: str
    descricao: str = ""
```

**Fundamentação (dois tipos vs. um tipo com campos opcionais):** optou-se por um segundo
tipo em vez de adicionar campos opcionais (`valor_brl=None`) ao `Transacao`. Razões:
(1) alinha com "cada transformação gera nova versão" — a conversão é uma transformação e
deve produzir um tipo novo; (2) evita estado ambíguo — um `Transacao` com `valor_brl=None`
representaria um dado "meio convertido", o que contradiz a clareza do paradigma; (3) o
campo `taxa_aplicada` dá **auditabilidade**: cada transação convertida carrega qual taxa
foi usada, sem depender de estado externo.

## 5. Componentes (Módulos)

### `modelos.py` *(já existe — será estendido)*
Define `Transacao` e `TransacaoConvertida`. Sem lógica, apenas estruturas de dados.

### `ingestao.py` — borda de I/O (leitura)
- `carregar_transacoes(caminho) -> list[Transacao]` — lê JSON, mapeia dicts → `Transacao`.
- `carregar_taxas(caminho) -> dict[str, float]` — lê `taxas.json` com a lógica de cache
  (ver Seção 6). É o único ponto que pode disparar rede, e apenas condicionalmente.

### `transformacao.py` — núcleo puro
- `normalizar(t: Transacao) -> Transacao` — padroniza campos (moeda em maiúsculas, data em
  formato único, descrição com trim).
- `converter(t: Transacao, taxas: dict) -> TransacaoConvertida` — aplica taxa, produz valor
  em BRL e registra `taxa_aplicada`.
- `filtrar(transacoes, criterio) -> list[TransacaoConvertida]` — função de alta ordem:
  recebe um predicado e retorna a sublista que o satisfaz.
- **Critérios-fábrica e combinadores** (ver Seção 7).

### `saida.py` — borda de I/O (escrita)
- `exportar_json(transacoes, caminho)` — grava `saida.json`.
- `gerar_relatorio(transacoes) -> dict` — consolida: total em BRL, contagem e soma por
  moeda de origem, valor médio.
- `imprimir_relatorio(relatorio)` — exibe no terminal.

### `fetch_taxas.py` — script standalone
- Busca taxas de câmbio em API real e grava `dados/taxas.json` com timestamp.
- Reutilizado pela borda `carregar_taxas` quando o cache precisa ser renovado.

### `main.py` — orquestrador
- Encadeia a pipeline: carregar → normalizar → converter → filtrar → exportar + relatório.

## 6. Estratégia de Câmbio: Cache com TTL

As taxas de câmbio vêm de uma API real, **mas a pipeline não toca rede no caminho normal**.

**Fundamentação (cache vs. API ao vivo vs. dois scripts manuais):** chamar a API a cada
execução reintroduziria latência de rede e tornaria a pipeline não-determinística e
dependente de conectividade. Por outro lado, exigir dois comandos manuais
(`fetch_taxas.py` e depois `main.py`) é frágil e fácil de esquecer. A solução adotada —
**cache com fallback na borda** — entrega um único ponto de execução (`main.py`) e dispara
rede apenas quando os dados estão ausentes ou expirados, preservando a pureza do núcleo.

**Formato de `dados/taxas.json`:**
```json
{
  "buscado_em": "2026-06-14T10:00:00",
  "taxas": { "USD": 5.40, "EUR": 5.90 }
}
```

**Lógica de `carregar_taxas`:**
1. **Vazio** → arquivo inexistente, não parseável, ou sem as moedas necessárias.
2. **Velho** → `agora - buscado_em > TTL`, com **TTL = 24h**.
3. Se vazio ou velho → chama `fetch_taxas`, grava, usa o resultado.
4. Se a API falhar mas existir cache (mesmo velho) → usa o cache e emite aviso.
5. Se a API falhar e não houver cache → erro explícito.

**Fundamentação do TTL de 24h:** câmbio é um dado de granularidade diária; uma taxa do dia
anterior é aceitável para o domínio. 24h evita buscas redundantes no mesmo dia sem deixar
os dados ficarem obsoletos. O timestamp é armazenado *dentro* do JSON (e não via `mtime`
do arquivo) para ser explícito e resistente a cópia/movimentação de arquivos.

## 7. Filtragem: Critérios e Combinadores

`filtrar` é uma função de alta ordem que recebe um predicado
`TransacaoConvertida -> bool`. Sobre ela, oferecemos um conjunto mínimo de fábricas de
critério e combinadores.

**Critérios base:**
- `valor_minimo(minimo)` — mantém se `valor_brl >= minimo`.
- `por_moeda(moeda)` — mantém se `moeda_original == moeda`.

**Combinadores:**
- `e_(*criterios)` — AND: passa se todos os critérios passam.
- `ou_(*criterios)` — OR: passa se algum critério passa.

```python
filtrar(txs, e_(valor_minimo(100), por_moeda("USD")))
# "USD acima de 100 BRL" — composição, sem código novo
```

**Fundamentação do conjunto:** dois predicados cobrem o domínio — `valor_minimo` atende
o requisito explícito do seminário ("acima de determinado valor", filtro de relevância) e
`por_moeda` atende o eixo central do sistema (multimoeda). Os dois combinadores dão poder
de composição ilimitado sem inchar a API: qualquer regra futura é apenas uma função
`TransacaoConvertida -> bool`, sem alterar `filtrar`. Esta é a demonstração concreta de
funções de alta ordem (recebem **e** retornam funções) — um ponto forte do paradigma
destacado no seminário. Aplicou-se YAGNI: nenhum critério adicional é incluído
especulativamente.

## 8. Tratamento de Erros

Política: **a borda valida, o núcleo confia.**

- **Ingestão:** arquivo ausente → erro claro. Transação malformada (campo faltando, valor
  não-numérico) → descarta com aviso, processa o restante.
- **Conversão:** moeda sem taxa correspondente → descarta a transação com aviso, não
  interrompe a pipeline.
- **Fetch:** falha de API → ver Seção 6 (fallback para cache ou erro explícito).
- **Núcleo** (`normalizar`, `converter`, `filtrar`) → assume dado válido, sem try/except
  interno. A validação aconteceu na borda de ingestão.

## 9. Testes (pytest)

As funções puras são triviais de testar — sem mocks, sem setup de rede. Isso reforça o
argumento do seminário de que o paradigma facilita testes.

- `test_transformacao.py` (foco) — `normalizar` (campos bagunçados), `converter` (cálculo
  BRL, taxa correta, moeda sem taxa), `filtrar` (cada critério, combinadores, lista vazia).
- `test_ingestao.py` — JSON válido, malformado e ausente.
- `test_saida.py` — relatório (totais, agregação por moeda, média) e gravação de JSON.
- Sem rede nos testes: taxas fornecidas via dict fixo ou arquivo temporário.

## 10. Escopo (YAGNI)

**Incluído:** pipeline completa, cache de taxas com TTL, filtragem componível, saída
JSON + relatório, testes das funções puras, script de fetch standalone.

**Fora de escopo:** múltiplas moedas-base (apenas BRL), persistência em banco de dados,
interface gráfica/web, suporte a formatos além de JSON, histórico/versionamento de taxas.

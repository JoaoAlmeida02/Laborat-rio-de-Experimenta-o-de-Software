# Laboratório 03: Mineração e Análise de Métricas DORA

Pipeline automatizado de coleta, mineração e consolidação de métricas DORA (*DevOps Research and Assessment*) a partir da API REST do GitHub.

---

## 1. Pré-requisitos e Instalação

Requer **Python 3.10 ou superior**.

Clone o repositório, crie e ative o ambiente virtual e instale as dependências:

```bash
cd LAB03
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

---

## 2. Configurar o Token do GitHub

Crie o arquivo `LAB03/.env` (ou na raiz do projeto) informando seu Personal Access Token do GitHub (*Settings → Developer settings → Personal access tokens*; nenhum escopo especial é necessário para repositórios públicos):

```env
GITHUB_TOKEN=ghp_seu_token_aqui
```

---

## 3. Como Rodar Tudo do Zero com Um Único Comando

Para executar o pipeline completo de ponta a ponta (seleção com critérios de inclusão, releases, workflow runs e consolidação):

```bash
python -m pipeline
```

Este comando único executa ordenadamente:
1. **Etapa 1 (Seleção e Funil):** busca candidatos por faixas de estrelas e aplica filtros estáticos, verificação de Actions e o critério de inclusão (**$\ge 5$ releases** e **$\ge 50$ workflow runs** na janela), gerando `data/repos.csv`, `data/funil.csv` e `data/funil.md`.
2. **Etapa 2 (Releases e Lead Time):** minera releases, tags e commits entre entregas, calculando Lead Time (a) e (b), CFR (b) e Rework Rate com a **Heurística v4**, gerando `data/lead_time_release.csv`.
3. **Etapa 3 (Workflow Runs e Recuperação):** coleta execuções mensais de CI com subdivisão adaptativa e checkpoint atômico, calculando CFR (a) (`cfr_ci`) e Tempo de Recuperação (`tempo_recuperacao`), gerando `data/metricas_runs.csv`.
4. **Etapa 4 (Consolidação e Proveniência):** combina todas as fontes no dataset final `data/dataset.csv` e gera o manifesto criptográfico `data/MANIFEST.json` com os hashes SHA-256 e metadados de execução.

> **Retomada transparente:** Se a execução for interrompida (por exemplo, via `Ctrl+C` ou término de rate limit), basta rodar o mesmo comando novamente. As requisições e períodos já coletados ficam salvos em cache (`.cache_http/` e `data/runs/`) e o pipeline continua exatamente de onde parou.

### 3.1 Execução via Docker (Container)

Caso prefira rodar o pipeline isolado em container Docker com um único comando:

```bash
# 1. Construir a imagem a partir do diretório LAB03/
docker build -t dora-pipeline .

# 2. Executar o pipeline montando o volume de dados e informando o token:
docker run -v $(pwd)/data:/app/data -e GITHUB_TOKEN=seu_token_aqui dora-pipeline
```

Parâmetros adicionais (como `--dry-run` ou `--etapa releases`) podem ser passados normalmente ao final do comando `docker run`.

---

## 4. Inovação: Modo `--dry-run` (Estimativa de Chamadas à API)

Antes de rodar a coleta completa, é possível simular e obter uma estimativa detalhada do consumo da API do GitHub:

```bash
python -m pipeline --dry-run
```

O comando exibirá o número projetado de requisições por etapa, o tempo estimado de execução considerando o rate limit de 5.000 req/hora e o impacto do cache.

---

## 5. Execução Modular por Etapas

Caso deseje rodar ou reprocessar etapas isoladas:

```bash
# Apenas a etapa de seleção e funil
python -m pipeline --etapa selecao

# Apenas a coleta de releases e lead time (após a seleção)
python -m pipeline --etapa releases

# Apenas a coleta de workflow runs de CI (após a seleção)
python -m pipeline --etapa runs

# Apenas a consolidação dos dados já coletados
python -m pipeline --etapa consolidar

# Forçar nova coleta ignorando o cache local
python -m pipeline --refazer
```

Parâmetros adicionais suportados:
- `--config config.yaml`: define um arquivo de configuração personalizado.
- `--limite 300`: sobrescreve a quantidade máxima de repositórios na amostra final.
- `--repos lista.csv`: executa diretamente sobre uma lista fornecida de repositórios, pulando a Etapa 1.

### 5.1 Replicação em Subamostra Específica de Repositórios (`--repos`)

Para replicadores que desejam reexecutar o pipeline sobre uma subamostra exata de repositórios (por exemplo, 30 repositórios sorteados de `data/dataset.csv` ou `data/repos.csv`) sem re-executar a busca dinâmica da Etapa 1:

```bash
# Executa etapas 2 (releases), 3 (runs) e 4 (consolidar) diretamente sobre a subamostra:
python -m pipeline --repos subamostra.csv

# Também compatível com estimativa prévia de requisições à API (--dry-run):
python -m pipeline --repos subamostra.csv --dry-run
```

**Comportamento:**
- Ao especificar `--repos <caminho.csv>`, a **Etapa 1 (busca e funil de seleção) é automaticamente ignorada**, garantindo estabilidade e reprodutibilidade exata, independente das contagens de estrelas no momento da execução.
- O pipeline consome o CSV indicado para minerar releases, workflow runs e consolidar o dataset final (`data/dataset.csv` e `data/MANIFEST.json`).
- Etapas isoladas também aceitam o parâmetro `--repos`:
  ```bash
  python -m pipeline --repos subamostra.csv --etapa releases
  python -m pipeline --repos subamostra.csv --etapa runs
  python -m pipeline --repos subamostra.csv --etapa consolidar
  ```

**Formato do arquivo de repositórios:**
O CSV aceita uma coluna `full_name` ou `repo` no formato `owner/repo_name`. Colunas adicionais de metadados (`stars`, `language`, `contribuidores`, etc.) são preservadas se presentes:

```csv
full_name
simdutf/simdutf
oxigraph/oxigraph
MAA1999/M9A
```

---

## 6. Validação e Avaliação da Amostra-Ouro (Heurística de Releases Corretivas)

Para avaliar a concordância interobservadores (Kappa de Fleiss e Cohen) e o desempenho das heurísticas (v0 a v4) contra a amostra rotulada:

```bash
# Análise de concordância entre os avaliadores (A, B e C)
python -m rotulagem.concordancia

# Avaliação de métricas de classificação (Precisão, Recall e F1-Score)
python -m rotulagem.avaliar_heuristica
```

Os resultados e matrizes de confusão são gerados em `rotulagem/avaliacao/` (ex.: `heuristicas_f1.csv`).

---

## 7. Análises: RQ 01 a 08 e Classificações DORA

Reexecutáveis offline a partir do dataset, sem chamadas à rede:

```bash
# RQ 01 a 04: Estatística descritiva e classificação de referência C1
python -m analises.rq01_04

# RQ 05: Correlação de Spearman entre frequência e CFR (a e b)
python -m analises.rq05

# RQ 06: Fatores determinantes (linguagem, estrelas, contribuidores, maturidade)
python -m analises.rq06

# RQ 07: Sensibilidade das combinações DORA (C1, C2, C3 e C4 filtrada)
python -m analises.rq07

# RQ 08 (Bônus): Rework Rate e associação com CFR (b)
python -m analises.rq08
```

Gera em `analises/saida/`:
- `RESUMO_RQ01_04.md`, `RESUMO_RQ07.md` e `RESUMO_RQ08.md`: tabelas prontas para o artigo;
- Tabelas de concordância (`rq07_concordancia.csv`), matrizes de transição (`rq07_transicao_C1_C2.csv`), Rework Rate (`rq08_correlacao.csv`);
- Gráficos e heatmaps em alta resolução (`fig_rq07_transicao_C1_C2.png`, `fig_rq08_rework_vs_cfr.png`).

---

## 8. Replicação Cruzada (Pipeline de Outro Grupo)

```bash
# Sorteia 30 repositórios do dataset original do outro grupo (semente 42)
python -m replicacao.executar subamostra --dataset <caminho/dataset_deles.csv> --n 30

# Executa o comando do README deles registrando log, ambiente e, se falhar, um rascunho de Issue
python -m replicacao.executar rodar --pasta <pasta_do_projeto_deles> -- <comando do README deles>
```

As evidências de cada tentativa ficam em `replicacao/execucoes/<data_hora>/` e o histórico em `replicacao/execucoes.csv`.

---

## 9. Testes Automatizados, Cobertura e Smoke Test

Para rodar toda a suíte de testes com relatório de cobertura de código:

```bash
python -m pytest --cov=metricas --cov=pipeline
```

Para executar o **smoke test** de ponta a ponta (verificação rápida offline com fixtures de cache e sem rede):

```bash
python -m pytest -m smoke
```

---

## 10. Estrutura dos Arquivos de Dados

- [`data/dataset.csv`](data/dataset.csv): dataset consolidado final com 1 linha por repositório (36 colunas). Consulte o [`DICIONARIO_DADOS.md`](DICIONARIO_DADOS.md) para a especificação completa de cada métrica.
- [`data/MANIFEST.json`](data/MANIFEST.json): manifesto com data/hora de coleta, commit Git, branch e hashes SHA-256 de todos os artefatos.
- [`data/funil.md`](data/funil.md) e `data/funil.csv`: tabela de funil das 7 etapas de seleção com critérios de inclusão.
- `data/repos.csv`: metadados dos repositórios selecionados (`full_name`, `owner`, `repo`, `stars`, `forks`, `open_issues`, `language`, `default_branch`, `created_at`, `idade_anos`, `idade_dias`, `contribuidores`). É o arquivo de entrada consumido pelas Etapas 2 (`releases`), 3 (`runs`) e 4 (`consolidar`). Pode ser substituído diretamente via `--repos <caminho.csv>` para replicação sobre qualquer subamostra.
- `data/lead_time_release.csv`: métricas de entregas e commits.
- `data/metricas_runs.csv`: métricas de CI/CD (CFR a e Tempo de Recuperação).

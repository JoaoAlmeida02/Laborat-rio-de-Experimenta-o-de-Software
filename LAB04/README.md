# LAB04 — Testes de hipótese por dentro

**Par de testes:** P4 — Teste Z para proporção × Teste binomial exato

**Pergunta:** a taxa de falha do CI do `pytest-dev/pytest` está acima da meta de 5%?

## Estrutura

```
LAB04/
├── dados/        dados reais coletados (CSV e resumo da coleta)
├── docs/         enunciado do laboratório
├── scripts/      código de coleta, simulação e testes
├── .env          token do GitHub (não versionado)
└── requirements.txt
```

## Como executar

```bash
cd LAB04
pip install -r requirements.txt
python scripts/coleta.py
```

## Dados reais

- **Fonte:** execuções do GitHub Actions do repositório [pytest-dev/pytest](https://github.com/pytest-dev/pytest/actions), obtidas pela API REST (`GET /repos/{owner}/{repo}/actions/runs`).
- **Filtros:** branch `main`, evento `push`, apenas execuções concluídas. São consideradas as 300 execuções mais recentes com conclusão `success`, `failure` ou `timed_out`; execuções canceladas ou puladas são descartadas, pois não indicam se o código passou ou falhou.
- **Falha:** `falha = 1` quando a conclusão é `failure` ou `timed_out`, e `falha = 0` quando é `success`.
- **Arquivos gerados:**
  - [`dados/ci_runs.csv`](dados/ci_runs.csv): uma linha por execução (`id`, `data`, `workflow`, `conclusao`, `falha`).
  - [`dados/resumo_coleta.md`](dados/resumo_coleta.md): período coberto, data da coleta, n, número de falhas e taxa observada.

A coleta exige um token do GitHub. Crie o arquivo `LAB04/.env` com a linha `GITHUB_TOKEN=seu_token`.

Outros repositórios ou filtros podem ser coletados com `python scripts/coleta.py --repo dono/repo --branch main --evento push --n 300`.

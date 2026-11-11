# LAB04 — Testes de hipótese por dentro

**Par de testes:** P4 — Teste Z para proporção × Teste binomial exato

**Pergunta:** a taxa de falha do CI do `pytest-dev/pytest` está acima da meta de 5%?

**Links do projeto:**
- [Repositório no GitHub](https://github.com/JoaoAlmeida02/Laborat-rio-de-Experimenta-o-de-Software)
- [GitHub Projects](https://github.com/JoaoAlmeida02/Laborat-rio-de-Experimenta-o-de-Software/projects)

## Estrutura

```
LAB04/
├── dados/            dados reais coletados (CSV e resumo da coleta)
├── docs/             enunciado, cenário e roteiro da apresentação oral
├── scripts/          coleta.py, simulacao.py, testes.py, erro_tipo1.py, poder.py
├── app.py            dashboard Streamlit
├── .env              token do GitHub (não versionado)
├── requirements.txt  dependências do projeto
└── README.md
```

## Como executar o dashboard

Com um único comando a partir da pasta `LAB04`:

```bash
cd LAB04
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura do Dashboard (`app.py`)

O dashboard contempla as 7 seções obrigatórias:
1. **Cenário:** formulação da pergunta, $H_0$, $H_1$, nível $\alpha = 0,05$ e contexto do repositório `pytest-dev/pytest`.
2. **Os dados (G1):** histograma do número de falhas por bloco de 30 execuções, comparando dados reais coletados e simulação calibrada ($\hat{p} = 0,0333$).
3. **Como os testes funcionam (G2):** distribuições sob $H_0$ (normal padrão no teste Z e distribuição discreta no binomial exato) com região crítica sombreada e destaque do p-valor.
4. **Erro tipo I (G3):** taxa de falsos alarmes em 10.000 simulações sob $H_0$ ($n = 300$ e amostras pequenas $n \in \{10, 20, 30, 50, 100\}$).
5. **Poder (G4):** curvas de poder estatístico para taxas reais de falha de 5% a 15% comparando amostra grande e pequenas.
6. **Dados reais:** tabela comparativa de estatística, p-valor, tamanho do efeito ($h$ de Cohen) e conclusão.
7. **Conclusão:** confronto entre expectativas prévias e resultados da simulação, recomendação técnica, quando a escolha mudaria e limitações.

O roteiro completo das 15 perguntas da apresentação oral está disponível em [`docs/roteiro_apresentacao.md`](docs/roteiro_apresentacao.md).

## Dados reais

- **Fonte:** execuções do GitHub Actions do repositório [pytest-dev/pytest](https://github.com/pytest-dev/pytest/actions), obtidas pela API REST (`GET /repos/{owner}/{repo}/actions/runs`).
- **Filtros:** branch `main`, evento `push`, apenas execuções concluídas. São consideradas as 300 execuções mais recentes com conclusão `success`, `failure` ou `timed_out`; execuções canceladas ou puladas são descartadas.
- **Falha:** `falha = 1` quando a conclusão é `failure` ou `timed_out`, e `falha = 0` quando é `success`.
- **Arquivos gerados:**
  - [`dados/ci_runs.csv`](dados/ci_runs.csv): 300 execuções (`id`, `data`, `workflow`, `conclusao`, `falha`).
  - [`dados/resumo_coleta.md`](dados/resumo_coleta.md): período coberto, data da coleta, n = 300, 10 falhas e taxa de 3,33%.

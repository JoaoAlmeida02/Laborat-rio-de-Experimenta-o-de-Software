# Funil de Selecao de Repositorios (LAB03)

Tabela de filtragem gerada automaticamente pelo pipeline de selecao com criterios de inclusao.

| Etapa | Repositorios Restantes | Descartados | Motivo do Descarte |
|:---|:---:|:---:|:---|
| 1. Candidatos da busca inicial (search/repositories) | 3385 | 0 | - |
| 2. Filtro estatico (descarte de forks) | 3385 | 0 | fork = true |
| 3. Filtro estatico (descarte de arquivados) | 3109 | 276 | archived = true |
| 4. Filtro estatico (descarte de espelhos) | 3109 | 0 | mirror_url presente |
| 5. Verificacao de CI/CD (GitHub Actions) | 2017 | 1092 | total_count == 0 em /actions/workflows |
| 6. ≥ 5 releases e ≥ 50 runs na janela | 300 | 1717 | < 5 releases ou < 50 workflow runs na janela |
| 7. Amostra final selecionada | 300 | 0 | limite_amostra alcancado |

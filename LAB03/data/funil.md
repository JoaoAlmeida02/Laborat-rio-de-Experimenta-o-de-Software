# Funil de Selecao de Repositorios (LAB03)

Tabela de filtragem gerada automaticamente pelo pipeline de selecao.

| Etapa | Repositorios Restantes | Descartados | Motivo do Descarte |
|:---|:---:|:---:|:---|
| 1. Candidatos da busca inicial (search/repositories) | 5000 | 0 | - |
| 2. Filtro estatico (descarte de forks) | 5000 | 0 | fork = true |
| 3. Filtro estatico (descarte de arquivados e mirrors) | 4999 | 1 | archived = true ou mirror |
| 4. Verificacao de CI/CD (GitHub Actions) | 4992 | 7 | total_count == 0 em /actions/workflows |
| 5. Amostra final selecionada | 5 | 4987 | limite_amostra alcancado |

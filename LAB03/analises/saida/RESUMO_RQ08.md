# RQ 08 (Bônus): Rework Rate e sua Associação com Change Failure Rate

Investigação da métrica de **Taxa de Retrabalho** (*Rework Rate*, introduzida no relatório DORA 2024):
- **Definição de release corretiva:** Heurística v4 validada (bump de patch SemVer + proporção de fixes ≥ features);
- **CFR (b):** proporção de releases seguidas de uma release corretiva em até 7 dias corridos.

## 1. Correlação de Spearman (Rework Rate vs CFR b)

- **Tamanho da amostra (n):** 299 repositórios com ambas as métricas avaliadas;
- **Coeficiente de Spearman (ρ):** **0.5782**;
- **Intervalo de Confiança 95% (Bootstrap):** [0.4853, 0.6641];
- **p-valor:** 4.56e-28 (estatisticamente altamente significativo a p < 0.001);
- **Interpretação:** Correlação positiva moderada: maior retrabalho associa-se a maior incidência de correções rápidas.

## 2. Estatística Descritiva por Categoria Geral DORA (C1)

| Categoria DORA | Repositórios | Rework Rate (Mediana) | Rework Rate (IQR) | CFR b (Mediana) | CFR b (IQR) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | 46 | 37.9% | 54.4% | 0.0% | 13.8% |
| **Medium** | 141 | 50.0% | 50.0% | 13.3% | 26.2% |
| **High** | 99 | 55.6% | 37.2% | 42.9% | 34.2% |
| **Elite** | 14 | 67.0% | 58.2% | 27.0% | 57.6% |
| **Total Geral** | 300 | 50.0% | 50.9% | 18.2% | 37.9% |

## 3. Discussão dos Resultados

A correlação positiva observada (ρ ≈ 0.58) demonstra forte alinhamento conceitual entre o Rework Rate e o CFR variante (b):
1. Repositórios com maior frequência de hotfixes e correções imediatas de bugs também concentram maior proporção de releases corretivas ao longo de todo o ciclo;
2. Equipes com categoria Elite na C1 tendem a manter ciclos de releases mais frequentes e cirúrgicos, enquanto categorias Low concentram menos deploys com grandes volumes cumulativos de correção.

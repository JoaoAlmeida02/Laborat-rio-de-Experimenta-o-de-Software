# Relatório de Replicação Cruzada e Reprodutibilidade

> Documento gerado automaticamente para suporte à Seção de Replicação Cruzada e Ameaças à Validade do Artigo SBC.

---

## 1. Síntese Geral da Concordância DORA

- **Repositórios Comparados:** 30
- **Mesma Classificação DORA Geral:** 27 (90.0%)
- **Kappa de Cohen Ponderado:** 0.8718
- **Distribuição de Deslocamentos de Categoria:**
  - 0 categorias (concordância exata): 27 (90.0%)
  - 1 categoria (ex: High → Medium): 3 (10.0%)
  - 2 ou mais categorias (ex: Elite → Medium): 0 (0.0%)

---

## 2. Diferenças Relativas por Métrica Individual

| Métrica Analisada | Repositórios Válidos | Mediana Dif. Relativa | [Q1, Q3] | IQR |
|---|---|---|---|---|
| CFR (a) CI | 30 | 5.01% | [2.09%, 28.26%] | 26.17% |
| CFR (b) entrega | 30 | 7.85% | [4.35%, 12.66%] | 8.31% |
| Deployment frequency | 30 | 2.77% | [1.44%, 3.69%] | 2.24% |
| Lead time (a) release | 30 | 4.18% | [3.32%, 6.54%] | 3.22% |
| Lead time (b) commit | 30 | 2.71% | [0.96%, 4.56%] | 3.59% |
| Tempo de recuperação | 24 | 9.07% | [6.16%, 11.77%] | 5.61% |

---

## 3. Análise das Causas de Divergência

1. **Evolução Temporal do Código (Novos Commits e Releases):** Como a API do GitHub reflete dados em tempo real, repositórios ativos continuam a receber commits e releases após a coleta original. Pequenas variações em Lead Time e CFR são esperadas decorrentes da janela móvel de datas de autor e datas de merge.
2. **Limites de Paginação e Rate Limit:** Algumas ferramentas atingem o teto de 1.000 workflow runs da busca caso não implementem a partição mensal exigida pela metodologia, truncando o cálculo de recuperação.
3. **Robusteza do Pipeline:** A concordância substancial de categorias (Kappa > 0.70) confirma que as inferências empíricas de velocidade e estabilidade DORA são reproduzíveis independentemente do executor.

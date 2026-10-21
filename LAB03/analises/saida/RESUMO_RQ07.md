# RQ 07: Sensibilidade das Métricas DORA a Variações Metodológicas

Avaliação do impacto de diferentes escolhas de unidade de entrega, variante de lead time e proxy de CFR:
- **C1 (Referência):** unidade release, lead time (a: release), CFR (a: CI);
- **C2:** unidade releases + pré-releases, lead time (b: commit), CFR (b: entrega);
- **C3:** unidade tags, lead time (b: commit), CFR (a: CI);
- **C4 (Filtrada):** C1 aplicada exclusivamente aos repositórios rotulados com entrega real na amostra-ouro.

## 1. Concordância e Estabilidade entre Combinações (Pares C1, C2, C3)

| Par de Combinações | n | Repositórios que Mudaram | % Mudança | Concordância (%) | Cohen's Kappa (linear) | Interpretação |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C1 x C2** | 300 | 94 | 31.33% | 68.67% | 0.5279 | Concordância moderada (moderate) |
| **C1 x C3** | 300 | 61 | 20.33% | 79.67% | 0.7252 | Concordância substancial (substantial) |
| **C2 x C3** | 300 | 65 | 21.67% | 78.33% | 0.7006 | Concordância substancial (substantial) |

## 2. Matriz de Transição C1 → C2 (Contagens Absolutas)

Mostra as mudanças de classificação quando se migra da combinação clássica (C1) para a combinação com commits e entregas corretivas (C2):

| C1 (Linhas) \ C2 (Colunas) | Low | Medium | High | Elite | Total C1 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | 33 | 11 | 2 | 0 | **46** |
| **Medium** | 5 | 118 | 17 | 1 | **141** |
| **High** | 3 | 43 | 52 | 1 | **99** |
| **Elite** | 1 | 5 | 5 | 3 | **14** |
| **Total C2** | 42 | 177 | 76 | 5 | **300** |

## 3. Análise da Configuração C4 ('Filtrada' por Entrega Real)

- **População da amostra-ouro rotulada:** 45 repositórios (45 com entregas reais);
- **Repositórios sobrepostos no dataset final (funil):** 4 repositórios (simdutf/simdutf, oxigraph/oxigraph, the-open-engine/zeroshot, elastic/elasticsearch-ruby);
- **Taxa de mudança C4 vs C1:** 0.0% (0 repositórios);
- **Cohen's Kappa linear:** 1.0 (Concordância quase perfeita (almost perfect));

> **Nota Metodológica:** Como documentado no funil e na amostra-ouro, apenas 4 repositórios da amostra rotulada atenderam aos critérios de inclusão (≥5 releases e ≥50 runs em 2025). As classificações C1 desses repositórios se mantêm inalteradas sob a regra de C4, pois todas as suas releases avaliadas constituíram entregas reais de valor.

# RQ 01 a 04 e classificação DORA de referência (C1)

Gerado por `python -m analises.rq01_04` a partir de `data/dataset.csv` (300 repositórios). Valores reportados como mediana e IQR (1º a 3º quartil), como pede o enunciado.

## Estatística descritiva (RQ 01 a 04)

| RQ | Métrica | Variante | n | Mediana | 1º quartil | 3º quartil | Categoria da mediana |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RQ 01 | Deployment frequency | - | 300 | 0,345 | 0,173 | 0,748 | Medium |
| RQ 02 | Lead time | (a) por release | 300 | 301,2 h (12,5 d) | 62,6 h (2,6 d) | 966,2 h (40,3 d) | Medium |
| RQ 02 | Lead time | (b) por commit | 300 | 261,1 h (10,9 d) | 72,1 h (3,0 d) | 735,0 h (30,6 d) | Medium |
| RQ 03 | Change failure rate | (a) proxy de CI | 300 | 5,1% | 1,3% | 14,5% | Elite |
| RQ 03 | Change failure rate | (b) proxy de entrega | 299 | 18,2% | 2,1% | 40,0% | High |
| RQ 04 | Tempo de recuperação | - | 261 | 13,8 h (0,6 d) | 2,1 h (0,1 d) | 47,2 h (2,0 d) | High |

## Classificação C1 (release, lead time (a), CFR (a) e recuperação)

| Métrica | n | Low | Medium | High | Elite | Sem valor |
| --- | --- | --- | --- | --- | --- | --- |
| Frequência de deploy | 300 | 102 (34,0%) | 135 (45,0%) | 61 (20,3%) | 2 (0,7%) | 0 |
| Lead time (a) | 300 | 90 (30,0%) | 90 (30,0%) | 75 (25,0%) | 45 (15,0%) | 0 |
| CFR (a) | 300 | 9 (3,0%) | 20 (6,7%) | 43 (14,3%) | 228 (76,0%) | 0 |
| Tempo de recuperação | 261 | 38 (14,6%) | 59 (22,6%) | 120 (46,0%) | 44 (16,9%) | 39 |
| Geral (C1) | 300 | 46 (15,3%) | 141 (47,0%) | 99 (33,0%) | 14 (4,7%) | 0 |

A categoria geral é a mediana das notas (Elite=4 … Low=1), arredondada para baixo. 39 repositórios não tiveram nenhum episódio de recuperação na janela; para eles a categoria geral usa as 3 métricas disponíveis (coluna `n_metricas`).

## Casos censurados e releases fora do cálculo

| RQ | Descrição | Valor | Total | % |
| --- | --- | --- | --- | --- |
| RQ 04 | repos sem nenhum episódio de recuperação na janela | 39 | 300 | 13,0% |
| RQ 04 | repos com algum episódio censurado | 89 | 300 | 29,7% |
| RQ 04 | mediana da proporção de episódios censurados por repo | 0 | – | – |
| RQ 04 | média da proporção de episódios censurados por repo | 0,0685 | – | – |
| RQ 04 | episódios de recuperação (total) | 4621 | – | – |
| RQ 03 (b) | releases censuradas (últimos 7 dias da janela) | 229 | 12381 | 1,8% |
| RQ 02 | releases sem release anterior | 44 | 12381 | 0,4% |
| RQ 02 | releases com compare indisponível (404/422) | 82 | 12381 | 0,7% |
| RQ 02 | releases sem commits novos | 1910 | 12381 | 15,4% |
| RQ 02 | repos com mediana do lead time (b) <= 0 (datas de autor posteriores à release) | 2 | 300 | 0,7% |

## Inovação: frequência efetiva (sem releases repetidas de monorepos)

Contando só releases com commits novos, a mediana da frequência passa de 0,345 para 0,345 releases/semana, e **12 repositórios (4,0%) mudam de categoria** de frequência. Dos 2 repositórios Elite em frequência, 2 deixam de ser Elite: a frequência alta vem de várias releases publicadas sobre o mesmo commit.

| Categoria original \ efetiva | Low | Medium | High | Elite |
| --- | --- | --- | --- | --- |
| Low | 102 | 0 | 0 | 0 |
| Medium | 3 | 132 | 0 | 0 |
| High | 0 | 7 | 54 | 0 |
| Elite | 0 | 2 | 0 | 0 |

Maiores diferenças:

| Repositório | Releases | Com commits novos | Freq. original | Freq. efetiva |
| --- | --- | --- | --- | --- |
| gajus/slonik | 468 | 36 | 8,975 | 0,690 |
| 0xPlaygrounds/rig | 386 | 40 | 7,403 | 0,767 |
| BuilderIO/builder | 248 | 49 | 4,756 | 0,940 |
| langchain-ai/langchainjs | 251 | 67 | 4,814 | 1,285 |
| resend/react-email | 193 | 71 | 3,701 | 1,362 |

## Limitação: sobreposição com a amostra-ouro

Apenas 4 dos 45 repositórios da amostra-ouro estão no dataset final, porque a amostra-ouro foi sorteada antes da aplicação do critério de inclusão. Por isso a comparação das categorias com o rótulo manual "entrega real" não tem tamanho de amostra suficiente e não é reportada.

## Figuras

- `fig_rq01_04_boxplots.png`: distribuição das métricas (RQ 01 a 04)
- `fig_categorias_C1.png`: distribuição das categorias DORA por métrica (C1)
- `fig_heatmap_C1.png`: perfil DORA de cada repositório (C1)

# Analise Estatistica - RQ1 e RQ2

**Sprint 03 - Issue #32 - LAB02**  
Fonte: `LAB02/Lab02S01/dados/resultados.csv`  
Total de trials: 12  

> **Trials censurados:** nenhum  

## 1. Analise Descritiva

Mediana e IQR por tratamento (todos os 12 trials, sem agregacao previa).

### RQ1 - Tempo (segundos)

| Tratamento | N | Mediana | IQR | Min | Max |
|------------|---|---------|-----|-----|-----|
| com_ia | 6 | 79.8 | 21.5 | 54.8 | 95.6 |
| sem_ia | 6 | 259.0 | 56.0 | 162.2 | 420.3 |

### RQ2 - Taxa de Sucesso

| Tratamento | N | Mediana | IQR | Min | Max |
|------------|---|---------|-----|-----|-----|
| com_ia | 6 | 100.0% | 0.0% | 100.0% | 100.0% |
| sem_ia | 6 | 83.3% | 21.4% | 50.0% | 100.0% |

## 2. Outliers (1.5xIQR por tratamento)

Apenas reportados - **nao removidos**.

### RQ1 - Tempo (s)

| trial_id | tratamento | valor | faixa valida | censurado |
|----------|------------|-------|--------------|-----------|
| Joao_kata4_escalonador_plantao_sem_ia | sem_ia | 420.3 | [152.925, 376.925] | - |

### RQ2 - Taxa de Sucesso

Nenhum outlier identificado.

## 3. Pares por Participante

Cada participante contribui com 1 par: mediana `com_ia` vs mediana `sem_ia`.

### RQ1 - Tempo (s)

| Pessoa | com_ia | sem_ia | delta (com - sem) |
|--------|--------|--------|-------------------|
| Joao | 79.8 | 291.2 | -211.4 |
| Lucas | 79.3 | 285.1 | -205.7 |
| Vitor | 75.2 | 240.8 | -165.7 |

### RQ2 - Taxa de Sucesso

| Pessoa | com_ia | sem_ia | delta (com - sem) |
|--------|--------|--------|-------------------|
| Joao | 100.0% | 91.7% | +8.3% |
| Lucas | 100.0% | 77.4% | +22.6% |
| Vitor | 100.0% | 75.0% | +25.0% |

## 4. Testes de Wilcoxon (pareado)

> **ATENCAO:** N=3 pares. Resultado **exploratorio** - poder estatistico baixo.

### RQ1 - Tempo

| Parametro | Valor |
|-----------|-------|
| N pares | 3 |
| Estatistica W | 0.0 |
| p-valor (bicaudal) | 0.2500 |
| Significativo (alfa=0.05)? | **Nao** (p >= 0.05) |

### RQ2 - Taxa de Sucesso

| Parametro | Valor |
|-----------|-------|
| N pares | 3 |
| Estatistica W | 0.0 |
| p-valor (bicaudal) | 0.2500 |
| Significativo (alfa=0.05)? | **Nao** (p >= 0.05) |

## 5. Interpretacao e Limitacoes

Com apenas **3 participantes** (N=3 pares), o poder estatistico do
Wilcoxon e muito baixo (~20% para efeitos moderados). Isso significa:

- **p-valor alto** nao implica ausencia de efeito (pode ser falta de poder).
- **p-valor baixo** deve ser tratado com cautela (risco de falso positivo).

Os indicadores mais confiáveis neste N sao:

1. **Direcao consistente** dos pares: todos os participantes apontam para
   o mesmo sentido da diferenca?
2. **Magnitude**: tamanho da mediana e do IQR por tratamento.
3. **Outliers censurados**: distorcao esperada pelo time-box.

**Recomendacao:** ampliar para >= 6 participantes em estudos futuros.

# Metricas estatisticas para analise DORA: tamanho de efeito, bootstrap e correcao de hipoteses.
import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu, spearmanr
from statsmodels.stats.multitest import multipletests


# Calcula o Cliff's Delta entre duas amostras independentes.
# Formula: delta = 2 * U1 / (n1 * n2) - 1
def cliffs_delta(x, y):
    x_clean = pd.to_numeric(pd.Series(x), errors="coerce").dropna().to_numpy(dtype=float)
    y_clean = pd.to_numeric(pd.Series(y), errors="coerce").dropna().to_numpy(dtype=float)
    n1 = len(x_clean)
    n2 = len(y_clean)
    if n1 == 0 or n2 == 0:
        return None
    # Caso particular onde todos os valores sao identicos
    if np.all(x_clean == x_clean[0]) and np.all(y_clean == x_clean[0]):
        return 0.0
    res = mannwhitneyu(x_clean, y_clean, alternative="two-sided")
    u1 = float(res.statistic)
    delta = (2.0 * u1 / (n1 * n2)) - 1.0
    return float(np.clip(delta, -1.0, 1.0))


# Classifica a magnitude de Cliff's Delta conforme Romano et al. (2006).
# |delta| < 0.147: desprezivel
# |delta| < 0.330: pequeno
# |delta| < 0.474: medio
# |delta| >= 0.474: grande
def interpretar_cliffs_delta(delta):
    if delta is None:
        return None
    mag = abs(delta)
    if mag < 0.147:
        return "desprezível"
    if mag < 0.330:
        return "pequeno"
    if mag < 0.474:
        return "médio"
    return "grande"


# Calcula o Epsilon-squared para o teste de Kruskal-Wallis.
# Formula oficial do laboratorio: eps2 = H / (n - 1)
def epsilon_squared_kruskal(h_stat, n):
    if h_stat is None or n is None or n <= 1:
        return None
    eps2 = float(h_stat) / float(n - 1)
    return float(np.clip(eps2, 0.0, 1.0))


# Classifica a magnitude de Epsilon-squared conforme recomendacoes usuais de literatura.
# < 0.01: desprezivel
# < 0.06: pequeno
# < 0.14: medio
# >= 0.14: grande
def interpretar_epsilon_squared(eps2):
    if eps2 is None:
        return None
    if eps2 < 0.01:
        return "desprezível"
    if eps2 < 0.06:
        return "pequeno"
    if eps2 < 0.14:
        return "médio"
    return "grande"


# Estima a correlacao de Spearman e intervalo de confianca via bootstrap pareado.
def bootstrap_spearman_ci(x, y, n_resamples=1000, conf_level=0.95, random_state=42):
    s_x = pd.to_numeric(pd.Series(x), errors="coerce")
    s_y = pd.to_numeric(pd.Series(y), errors="coerce")
    valido = s_x.notna() & s_y.notna()
    x_arr = s_x[valido].to_numpy(dtype=float)
    y_arr = s_y[valido].to_numpy(dtype=float)
    n = len(x_arr)
    if n < 3:
        return {
            "rho": None,
            "p_valor": None,
            "ci_inferior": None,
            "ci_superior": None,
            "n": n,
        }
    res_ponto = spearmanr(x_arr, y_arr)
    rho_ponto = float(res_ponto.statistic)
    p_valor = float(res_ponto.pvalue)

    # Reamostragem bootstrap pareada com semente pseudoaleatoria deterministica
    rng = np.random.default_rng(random_state)
    rhos = []
    indices = np.arange(n)
    for _ in range(n_resamples):
        idx = rng.choice(indices, size=n, replace=True)
        r = spearmanr(x_arr[idx], y_arr[idx]).statistic
        if not np.isnan(r):
            rhos.append(float(r))

    if len(rhos) == 0:
        return {
            "rho": rho_ponto,
            "p_valor": p_valor,
            "ci_inferior": None,
            "ci_superior": None,
            "n": n,
        }

    alpha = (1.0 - conf_level) / 2.0
    ci_inf = float(np.percentile(rhos, 100.0 * alpha))
    ci_sup = float(np.percentile(rhos, 100.0 * (1.0 - alpha)))

    return {
        "rho": rho_ponto,
        "p_valor": p_valor,
        "ci_inferior": ci_inf,
        "ci_superior": ci_sup,
        "n": n,
    }


# Aplica a correcao de Holm-Bonferroni sobre uma lista ou serie de p-valores.
def corrigir_pvalores_holm(p_valores, alfa=0.05):
    p_clean = [1.0 if (p is None or np.isnan(p)) else float(p) for p in p_valores]
    if len(p_clean) == 0:
        return {"rejeicoes": [], "p_corrigidos": []}
    rejeicoes, p_corrigidos, _, _ = multipletests(p_clean, alpha=alfa, method="holm")
    return {
        "rejeicoes": [bool(r) for r in rejeicoes],
        "p_corrigidos": [float(p) for p in p_corrigidos],
    }

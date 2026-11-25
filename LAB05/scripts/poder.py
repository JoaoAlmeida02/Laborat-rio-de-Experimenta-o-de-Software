"""Análise de poder do experimento fatorial 2x2 (RQ1 e RQ2): define k e confere a margem (LAB05S01, João).

Pergunta: quantas repetições k por tratamento (T1..T4) precisamos para que o teste de
equivalência (TOST, margem de +-5%) consiga concluir "equivalente" quando a correção
realmente não custa desempenho?

Método (simulação, como no LAB04):
  1. A variabilidade vem do piloto do Vitor (dados/piloto/*.csv). Cada métrica é analisada
     em escala log, então o desvio-padrão sigma dos logs é o coeficiente de variação relativo.
     Com só 2 repetições por tratamento o sigma é incerto: usamos o limite superior de um
     intervalo de confiança de 80% (qui-quadrado), para não subestimar k.
  2. Para cada k, simulamos o experimento 2x2 inteiro (4 tratamentos x k repetições) e
     aplicamos o TOST ao efeito principal da versão (e da mitigação) sobre o log da métrica.
     Poder = fração das simulações em que o TOST conclui equivalência.
  3. k = menor valor com poder >= 80% na PIOR métrica (a mais ruidosa, em geral p99), por
     causa da Lei de Goodhart: não adianta ter poder só para a média.
  4. Também calculamos o poder para DETECTAR uma diferença real (5% e 10%) e a menor margem
     de equivalência que o k escolhido consegue confirmar.

Sem o piloto, usa valores ASSUMIDOS de sigma e avisa claramente. Rode de novo quando
dados/piloto/ existir.

Formato esperado dos CSVs do piloto (um por execução ou um só, colunas mínimas):
    tratamento (T1..T4), repeticao, rps, p50_ms, p95_ms, p99_ms [, mem_mb, erro_pct]

Saída: resultados/poder_k.csv e resumo no terminal.

Uso (a partir da pasta LAB05):
    python scripts/poder.py [--piloto dados/piloto] [--margem 0.05] [--alvo 0.8]
"""
import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, t

RAIZ = Path(__file__).resolve().parents[1]
PILOTO = RAIZ / "dados" / "piloto"
SAIDA = RAIZ / "resultados" / "poder_k.csv"

ALFA = 0.05
MARGEM = 0.05  # equivalência: a razão entre versões fica dentro de 1/1.05 .. 1.05
PODER_ALVO = 0.80
REPS = 10_000
SEMENTE = 42
K_MAX = 40
NIVEL_CONF_SIGMA = 0.80  # limite superior do sigma do piloto
METRICAS = ["rps", "p50_ms", "p95_ms", "p99_ms"]
TRATAMENTOS = ["T1", "T2", "T3", "T4"]  # T1 8.4.26 s/ mit, T2 8.4.26 c/ mit, T3 8.4.27 s/ mit, T4 8.4.27 c/ mit

# Usados SÓ se não houver piloto. São suposições de ordem de grandeza para benchmarks em Docker.
SIGMA_ASSUMIDO = {"rps": 0.03, "p50_ms": 0.04, "p95_ms": 0.08, "p99_ms": 0.15}


def criar_rng(semente=SEMENTE):
    return np.random.default_rng(semente)


def ler_piloto(pasta=PILOTO):
    """Junta todos os CSVs do piloto. Devolve DataFrame ou None se não houver dados."""
    arquivos = sorted(Path(pasta).glob("*.csv")) if Path(pasta).exists() else []
    quadros = []
    for a in arquivos:
        df = pd.read_csv(a)
        if {"tratamento", *METRICAS}.issubset(df.columns):
            if "endpoint" in df.columns:
                df = df[df["endpoint"] == "geral"]
            quadros.append(df)
    return pd.concat(quadros, ignore_index=True) if quadros else None


def sigma_log_agrupado(df, metrica):
    """Desvio-padrão dos logs dentro de cada tratamento (agrupado) e graus de liberdade."""
    y = np.log(df[metrica].astype(float))
    desvios = y - y.groupby(df["tratamento"]).transform("mean")
    n = len(df)
    gl = n - df["tratamento"].nunique()
    if gl <= 0:
        raise ValueError("o piloto precisa de pelo menos 2 repetições por tratamento")
    return float(np.sqrt((desvios**2).sum() / gl)), int(gl)


def sigma_superior(sigma, gl, nivel=NIVEL_CONF_SIGMA):
    """Limite superior unilateral do sigma (qui-quadrado), para não subestimar a variabilidade."""
    return float(sigma * np.sqrt(gl / chi2.ppf(1 - nivel, gl)))


def sigmas_do_piloto(df):
    """Devolve {metrica: (sigma, sigma_superior, gl, origem)}."""
    if df is None:
        return {m: (s, s, None, "assumido") for m, s in SIGMA_ASSUMIDO.items()}
    saida = {}
    for m in METRICAS:
        s, gl = sigma_log_agrupado(df, m)
        saida[m] = (s, sigma_superior(s, gl), gl, "piloto")
    return saida


def simular_tost(k, sigma, efeito=0.0, margem=MARGEM, reps=REPS, alfa=ALFA, rng=None):
    """Poder do TOST e do teste de diferença para o efeito principal de um fator do 2x2.

    k: repetições por tratamento; sigma: desvio-padrão dos logs; efeito: diferença real
    relativa (0.02 = +2%) do fator, aplicada nos 2 tratamentos do nível alto.

    Devolve (poder_equivalencia, poder_diferenca).
    """
    rng = rng or criar_rng()
    delta = np.log1p(efeito)
    # tratamentos 0,1 = nível baixo do fator; 2,3 = nível alto (a divisão em dois níveis do outro
    # fator não altera o contraste do efeito principal)
    media = np.array([0.0, 0.0, delta, delta])
    y = rng.normal(media[None, :, None], sigma, size=(reps, 4, k))
    gl = 4 * (k - 1)
    s2 = y.var(axis=2, ddof=1).mean(axis=1)  # variância residual agrupada
    dif = y[:, 2:, :].mean(axis=(1, 2)) - y[:, :2, :].mean(axis=(1, 2))
    ep = np.sqrt(s2 * (1 / (2 * k) + 1 / (2 * k)))
    lim = np.log1p(margem)
    tcrit = t.ppf(1 - alfa, gl)
    # TOST: rejeita H0 (não equivalência) se as duas hipóteses unilaterais forem rejeitadas
    equivalente = ((dif + lim) / ep > tcrit) & ((lim - dif) / ep > tcrit)
    # teste bilateral de diferença (equivale ao F do efeito principal, 1 gl no numerador)
    diferente = np.abs(dif / ep) > t.ppf(1 - alfa / 2, gl)
    return float(equivalente.mean()), float(diferente.mean())


def poder_por_k(sigma, ks, margem=MARGEM, reps=REPS, semente=SEMENTE):
    linhas = []
    for k in ks:
        p_eq0, _ = simular_tost(k, sigma, 0.0, margem, reps, rng=criar_rng(semente))
        p_eq2, _ = simular_tost(k, sigma, 0.02, margem, reps, rng=criar_rng(semente))
        _, p_d5 = simular_tost(k, sigma, 0.05, margem, reps, rng=criar_rng(semente))
        _, p_d10 = simular_tost(k, sigma, 0.10, margem, reps, rng=criar_rng(semente))
        linhas.append({"k": k, "poder_equiv_efeito0": p_eq0, "poder_equiv_efeito2pct": p_eq2, "poder_detecta_5pct": p_d5, "poder_detecta_10pct": p_d10})
    return pd.DataFrame(linhas)


def menor_k(df_poder, alvo=PODER_ALVO, coluna="poder_equiv_efeito0"):
    ok = df_poder[df_poder[coluna] >= alvo]
    return int(ok["k"].min()) if len(ok) else None


def menor_margem(k, sigma, alvo=PODER_ALVO, reps=2_000, semente=SEMENTE):
    """Menor margem de equivalência (em %) que o k consegue confirmar com o poder-alvo (efeito real 0)."""
    for m in np.arange(0.01, 0.31, 0.005):
        p, _ = simular_tost(k, sigma, 0.0, float(m), reps, rng=criar_rng(semente))
        if p >= alvo:
            return round(float(m), 3)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--piloto", default=str(PILOTO))
    ap.add_argument("--margem", type=float, default=MARGEM)
    ap.add_argument("--alvo", type=float, default=PODER_ALVO)
    ap.add_argument("--reps", type=int, default=REPS)
    a = ap.parse_args()

    df = ler_piloto(a.piloto)
    if df is None:
        print("AVISO: nenhum CSV de piloto em", a.piloto)
        print("       usando sigma ASSUMIDO (suposição). Rode de novo com os dados do Vitor.\n")
    sigmas = sigmas_do_piloto(df)
    ks = range(2, K_MAX + 1)

    linhas, k_por_metrica = [], {}
    print(f"{'métrica':<8}{'origem':<9}{'sigma':>8}{'sigma_sup':>11}{'k mínimo':>10}{'margem mín. (k)':>17}")
    for m in METRICAS:
        s, s_sup, gl, origem = sigmas[m]
        tabela = poder_por_k(s_sup, ks, a.margem, a.reps)
        k = menor_k(tabela, a.alvo)
        k_por_metrica[m] = k
        marg = menor_margem(k, s_sup, a.alvo) if k else None
        print(f"{m:<8}{origem:<9}{s:>8.3f}{s_sup:>11.3f}{str(k or f'>{K_MAX}'):>10}{(f'+-{marg:.1%}' if marg else '-'):>17}")
        for _, r in tabela.iterrows():
            linhas.append({"metrica": m, "origem": origem, "sigma": round(s, 4), "sigma_sup": round(s_sup, 4), **r.to_dict(), "margem": a.margem})

    validos = [k for k in k_por_metrica.values() if k]
    k_final = max(validos) if len(validos) == len(METRICAS) else None
    pior = max(k_por_metrica, key=lambda m: k_por_metrica[m] or K_MAX + 1)
    print()
    if k_final:
        print(f"k recomendado = {k_final} repetições por tratamento ({4 * k_final} execuções no total),")
        print(f"definido pela métrica mais ruidosa ({pior}). Poder alvo: {a.alvo:.0%}, margem +-{a.margem:.0%}, alfa {ALFA}.")
    else:
        print(f"Nenhum k <= {K_MAX} atinge poder {a.alvo:.0%} para margem +-{a.margem:.0%} em todas as métricas:")
        print("  considere uma margem maior para as métricas de cauda (p99) e justifique.")
    if df is None:
        print("ATENÇÃO: valor provisório (sigma assumido). Não use para justificar o k final.")
    SAIDA.parent.mkdir(exist_ok=True)
    with SAIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"Tabela completa em {SAIDA}")


if __name__ == "__main__":
    main()

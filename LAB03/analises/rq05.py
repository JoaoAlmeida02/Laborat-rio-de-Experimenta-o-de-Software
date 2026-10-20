# Analise da RQ 05: Correlacao de Spearman entre Deployment Frequency e CFR (a e b).
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from metricas.estatistica import bootstrap_spearman_ci

RAIZ = Path(__file__).resolve().parents[1]
SUPERFICIE, TINTA, TINTA_SEC, TINTA_MUDA, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COR_MARCA = "#2a78d6"
COR_SECUNDARIA = "#1c5cab"


# Calcula a correlacao de Spearman com intervalo de confianca por bootstrap para duas colunas do dataset.
def calcular_correlacao_par(df, col_x, col_y, rotulo_y, variante_y, n_resamples=1000, random_state=42):
    s = df[[col_x, col_y]].dropna()
    res = bootstrap_spearman_ci(s[col_x], s[col_y], n_resamples=n_resamples, random_state=42)
    rho = res["rho"]
    p_val = res["p_valor"]
    ci_inf = res["ci_inferior"]
    ci_sup = res["ci_superior"]
    n = res["n"]

    interp = "Sem correlação estatisticamente significativa"
    if p_val is not None and p_val < 0.05:
        if rho > 0:
            interp = "Correlação positiva fraca/moderada: maior frequência associada a maior taxa de falha"
        else:
            interp = "Correlação negativa: maior frequência associada a menor taxa de falha (suporte a DORA)"

    return {
        "rq": "RQ 05",
        "par": f"{col_x}_vs_{col_y}",
        "metrica_x": "Deployment frequency",
        "metrica_y": rotulo_y,
        "variante_y": variante_y,
        "coluna_x": col_x,
        "coluna_y": col_y,
        "n": n,
        "rho": round(rho, 4) if rho is not None else None,
        "p_valor": p_val,
        "p_valor_formatado": f"{p_val:.2e}" if (p_val is not None and p_val < 0.001) else (f"{p_val:.4f}" if p_val is not None else "-"),
        "ci_inferior_95": round(ci_inf, 4) if ci_inf is not None else None,
        "ci_superior_95": round(ci_sup, 4) if ci_sup is not None else None,
        "significativo_5pct": bool(p_val is not None and p_val < 0.05),
        "interpretacao": interp,
    }


# Executa o calculo completo da RQ 05 para ambas as variantes de CFR.
def tabela_rq05(df, n_resamples=1000, random_state=42):
    pares = [
        ("deploy_frequency_semana", "cfr_ci", "Change failure rate", "(a) Proxy de CI"),
        ("deploy_frequency_semana", "cfr_entrega", "Change failure rate", "(b) Proxy de entrega"),
    ]
    linhas = []
    for cx, cy, rot, var in pares:
        linhas.append(calcular_correlacao_par(df, cx, cy, rot, var, n_resamples=n_resamples, random_state=random_state))
    return pd.DataFrame(linhas)


# Formata os eixos de graficos com estetica limpa.
def _estilo(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c3c2b7")
    ax.tick_params(colors=TINTA_MUDA, labelcolor=TINTA_SEC, labelsize=9)
    ax.grid(True, color=GRADE, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)


# Gera os graficos de dispersao em escala logaritmica para a RQ 05.
def gerar_grafico_rq05(df, res_tabela, caminho_figura):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), facecolor=SUPERFICIE)

    # Subplot A: Frequencia vs CFR (a) - CI
    res_a = res_tabela[res_tabela["coluna_y"] == "cfr_ci"].iloc[0]
    dados_a = df[["deploy_frequency_semana", "cfr_ci"]].dropna()
    dados_a = dados_a[dados_a["deploy_frequency_semana"] > 0]
    ax1.scatter(dados_a["deploy_frequency_semana"], dados_a["cfr_ci"] * 100.0,
                color=COR_MARCA, alpha=0.45, edgecolors="none", s=36, label="Repositórios")
    ax1.set_xscale("log")
    ax1.set_xlabel("Frequência de deploy (releases/semana, escala log)", color=TINTA_SEC, fontsize=9.5)
    ax1.set_ylabel("CFR (a) - Proxy de CI (% de runs com falha)", color=TINTA_SEC, fontsize=9.5)
    ax1.set_title("RQ 05 (a) · Frequência vs. Falhas de CI", loc="left", fontsize=11, color=TINTA, fontweight="bold")
    _estilo(ax1)

    texto_a = (
        f"Spearman ρ = {res_a['rho']:.4f}\n"
        f"IC 95% bootstrap: [{res_a['ci_inferior_95']:.4f}, {res_a['ci_superior_95']:.4f}]\n"
        f"p-valor = {res_a['p_valor_formatado']}\n"
        f"n = {res_a['n']}"
    )
    ax1.text(0.04, 0.94, texto_a, transform=ax1.transAxes, fontsize=8.5, verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#c3c2b7", alpha=0.9))

    # Subplot B: Frequencia vs CFR (b) - Entrega
    res_b = res_tabela[res_tabela["coluna_y"] == "cfr_entrega"].iloc[0]
    dados_b = df[["deploy_frequency_semana", "cfr_entrega"]].dropna()
    dados_b = dados_b[dados_b["deploy_frequency_semana"] > 0]
    ax2.scatter(dados_b["deploy_frequency_semana"], dados_b["cfr_entrega"] * 100.0,
                color=COR_SECUNDARIA, alpha=0.45, edgecolors="none", s=36, label="Repositórios")
    ax2.set_xscale("log")
    ax2.set_xlabel("Frequência de deploy (releases/semana, escala log)", color=TINTA_SEC, fontsize=9.5)
    ax2.set_ylabel("CFR (b) - Proxy de entrega (% releases corretivas em 7d)", color=TINTA_SEC, fontsize=9.5)
    ax2.set_title("RQ 05 (b) · Frequência vs. Releases Corretivas", loc="left", fontsize=11, color=TINTA, fontweight="bold")
    _estilo(ax2)

    texto_b = (
        f"Spearman ρ = {res_b['rho']:.4f}\n"
        f"IC 95% bootstrap: [{res_b['ci_inferior_95']:.4f}, {res_b['ci_superior_95']:.4f}]\n"
        f"p-valor = {res_b['p_valor_formatado']}\n"
        f"n = {res_b['n']}"
    )
    ax2.text(0.04, 0.94, texto_b, transform=ax2.transAxes, fontsize=8.5, verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#c3c2b7", alpha=0.9))

    fig.text(0.01, 0.01, "Nota: Eixo X em escala log. Correlação de postos de Spearman não assume normalidade nem linearidade.",
             fontsize=8, color=TINTA_MUDA)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho_figura, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)


# Funcao principal que coordena a execucao da RQ 05 e grava os arquivos de saida.
def executar(caminho_dataset, pasta_saida, n_resamples=1000, random_state=42):
    df = pd.read_csv(caminho_dataset)
    saida = Path(pasta_saida)
    saida.mkdir(parents=True, exist_ok=True)

    tabela = tabela_rq05(df, n_resamples=n_resamples, random_state=random_state)
    caminho_csv = saida / "rq05_correlacao.csv"
    tabela.to_csv(caminho_csv, index=False, encoding="utf-8")

    caminho_fig = saida / "fig_rq05_spearman.png"
    gerar_grafico_rq05(df, tabela, caminho_fig)

    return {
        "tabela": tabela,
        "caminho_csv": caminho_csv,
        "caminho_figura": caminho_fig,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="RQ 05: Correlacao entre Frequencia e CFR (a e b).")
    parser.add_argument("--dataset", default=str(RAIZ / "data" / "dataset.csv"), help="Caminho do dataset consolidado")
    parser.add_argument("--saida", default=str(RAIZ / "analises" / "saida"), help="Pasta de saida")
    parser.add_argument("--n-resamples", type=int, default=1000, help="Reamostragens bootstrap")
    parser.add_argument("--semente", type=int, default=42, help="Semente pseudoaleatoria fixa")
    args = parser.parse_args(argv)

    print(f"Executando analise da RQ 05 sobre {args.dataset}...")
    res = executar(args.dataset, args.saida, n_resamples=args.n_resamples, random_state=args.semente)
    print(f"Resultados salvos em:\n - {res['caminho_csv']}\n - {res['caminho_figura']}")
    print("\nTabela resumida:")
    print(res["tabela"][["par", "n", "rho", "p_valor_formatado", "ci_inferior_95", "ci_superior_95", "significativo_5pct"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())

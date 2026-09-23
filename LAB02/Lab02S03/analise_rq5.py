"""
Analise da RQ5: Indice de Desempenho Global (IDG).

Mapeia a RQ5 do experimento LAB02:
"O uso de assistente de IA melhora o desempenho global do desenvolvedor,
considerando simultaneamente velocidade, correcao e manutenibilidade do codigo?"

IDG = (1 - tempo_norm) * 1/3  +  taxa_sucesso_norm * 1/3  +  MI_norm * 1/3
Cada dimensao normalizada min-max para [0, 1].

Uso:
    python LAB02/Lab02S03/analise_rq5.py

Gera:
    - resumo_rq5.csv         : estatisticas descritivas do IDG por tratamento
    - graficos/rq5_idg.png   : violin do IDG + swarm de pontos por pessoa
    - graficos/rq_violinos.png: painel unico com violinos de todas as RQs
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
DADOS_CSV = BASE / "dados_consolidados.csv"
GRAFICOS = BASE / "graficos"
SAIDA_RESUMO_RQ5 = BASE / "resumo_rq5.csv"

# ---------------------------------------------------------------------------
# Paleta visual identica aos demais scripts
# ---------------------------------------------------------------------------
ORDEM = ["sem_ia", "com_ia"]
ROTULO = {"sem_ia": "Sem IA", "com_ia": "Com IA"}
COR = {"sem_ia": "#eb6834", "com_ia": "#2a78d6"}
MARCADOR = {"Joao": "o", "Lucas": "s", "Vitor": "^"}

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUDA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"

plt.rcParams.update(
    {
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "axes.edgecolor": EIXO,
        "axes.labelcolor": TINTA_2,
        "axes.titlecolor": TINTA,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "xtick.color": TINTA_MUDA,
        "ytick.color": TINTA_MUDA,
        "xtick.labelcolor": TINTA_2,
        "ytick.labelcolor": TINTA_2,
        "text.color": TINTA,
        "font.size": 9.5,
    }
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def norm_minmax(s: pd.Series) -> pd.Series:
    """Normaliza uma serie para [0, 1] via min-max."""
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(np.ones(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def calc_iqr(s: pd.Series) -> float:
    return float(s.quantile(0.75) - s.quantile(0.25))


def violin_ax(ax, grupos, cores, rotulos, ylabel, title):
    """
    Desenha um violin plot num eixo matplotlib.
    grupos : lista de arrays (um por tratamento)
    """
    # Filtra grupos vazios ou com variancia zero (violinplot exige >= 2 pts distintos)
    validos = [g for g in grupos if len(g) >= 2 and np.std(g) > 0]
    pos_validas = [i for i, g in enumerate(grupos) if len(g) >= 2 and np.std(g) > 0]

    if validos:
        parts = ax.violinplot(
            validos,
            positions=pos_validas,
            widths=0.5,
            showmedians=True,
            showextrema=True,
        )
        for pc, i in zip(parts["bodies"], pos_validas):
            pc.set_facecolor(cores[i])
            pc.set_edgecolor(TINTA_2)
            pc.set_alpha(0.55)
        for partname in ("cmedians", "cmins", "cmaxes", "cbars"):
            parts[partname].set_color(TINTA_2)
            parts[partname].set_linewidth(1.2)

    # Pontos individuais sobre o violin
    rng = np.random.default_rng(7)
    for i, grupo in enumerate(grupos):
        jitter = rng.uniform(-0.08, 0.08, len(grupo))
        ax.scatter(
            np.full(len(grupo), i) + jitter,
            grupo,
            color=cores[i],
            edgecolor=TINTA,
            linewidth=0.6,
            s=45,
            zorder=4,
            alpha=0.9,
        )

    ax.set_xticks(range(len(rotulos)))
    ax.set_xticklabels(rotulos, fontsize=9.5)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title)
    ax.grid(axis="x", visible=False)


# ---------------------------------------------------------------------------
# Carga e calculo do IDG
# ---------------------------------------------------------------------------

def carregar_e_calcular(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {csv_path}")

    df = pd.read_csv(csv_path)

    # Metricas derivadas necessarias
    df["densidade_cc_sloc"] = df["cc_total"] / df["sloc"].replace(0, np.nan)

    # Normalizacao min-max global (sobre todos os trials)
    df["tempo_norm"] = norm_minmax(df["tempo_segundos"])
    df["taxa_norm"] = norm_minmax(df["taxa_sucesso"])
    df["mi_norm"] = norm_minmax(df["indice_manutenibilidade"])

    # IDG com pesos iguais (1/3 cada dimensao)
    # (1 - tempo_norm) porque menor tempo = melhor
    df["IDG"] = ((1 - df["tempo_norm"]) + df["taxa_norm"] + df["mi_norm"]) / 3

    return df


# ---------------------------------------------------------------------------
# Estatisticas descritivas RQ5
# ---------------------------------------------------------------------------

def calcular_resumo_rq5(df: pd.DataFrame) -> pd.DataFrame:
    registros = []
    for t in ORDEM:
        s = df.loc[df.tratamento == t, "IDG"].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        registros.append(
            {
                "tratamento": t,
                "n": len(s),
                "mediana": round(s.median(), 4),
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "iqr": round(q3 - q1, 4),
                "media": round(s.mean(), 4),
                "desvio_padrao": round(s.std(), 4),
                "min": round(s.min(), 4),
                "max": round(s.max(), 4),
            }
        )
    return pd.DataFrame(registros)


# ---------------------------------------------------------------------------
# Grafico 1: IDG detalhado (RQ5)
# ---------------------------------------------------------------------------

def plotar_rq5_idg(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    cores_lista = [COR[t] for t in ORDEM]
    rotulos_lista = [ROTULO[t] for t in ORDEM]

    # Painel 1: Violin IDG
    grupos_idg = [df.loc[df.tratamento == t, "IDG"].dropna().values for t in ORDEM]
    violin_ax(axes[0], grupos_idg, cores_lista, rotulos_lista,
              "IDG (0 = pior, 1 = melhor)", "Indice de Desempenho Global (IDG)")

    # Anotar mediana
    for i, (t, grupo) in enumerate(zip(ORDEM, grupos_idg)):
        if len(grupo):
            med = np.median(grupo)
            axes[0].text(i + 0.28, med, f"{med:.3f}",
                         va="center", fontsize=8, color=TINTA_2)

    # Painel 2: IDG pareado por pessoa (dot-line)
    pessoas = sorted(df["pessoa"].unique())
    med_p = df.groupby(["pessoa", "tratamento"])["IDG"].median().unstack()
    for y, p in enumerate(pessoas):
        axes[1].hlines(y, med_p.loc[p].min(), med_p.loc[p].max(),
                       color=EIXO, lw=3, zorder=1)
        for t in ORDEM:
            axes[1].scatter(
                med_p.loc[p, t], y,
                s=75, color=COR[t], marker=MARCADOR[p],
                zorder=3, edgecolor=SUPERFICIE, linewidth=1.2,
            )
            axes[1].annotate(
                f"{med_p.loc[p, t]:.3f}",
                (med_p.loc[p, t], y),
                textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=8, color=TINTA_2,
            )
    axes[1].set_yticks(range(len(pessoas)))
    axes[1].set_yticklabels(pessoas)
    axes[1].set_ylim(-0.6, len(pessoas) - 0.4)
    axes[1].invert_yaxis()
    axes[1].set_title("IDG Pareado por Participante")
    axes[1].set_xlabel("IDG (0-1, maior = melhor)")
    axes[1].grid(axis="y", visible=False)

    # Legenda global
    itens = [mpatches.Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    itens += [Line2D([], [], marker=m, color=TINTA_MUDA, linestyle="",
                     markersize=7, label=p) for p, m in MARCADOR.items()]
    fig.legend(handles=itens, loc="lower center", ncol=5,
               frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.0))

    fig.suptitle(
        "RQ5: Indice de Desempenho Global (IDG) — Velocidade + Correcao + Manutenibilidade",
        x=0.03, ha="left", fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))

    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = GRAFICOS / "rq5_idg.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print(f"grafico gerado: {caminho.name}")


# ---------------------------------------------------------------------------
# Grafico 2: Painel unificado com violinos de TODAS as RQs
# ---------------------------------------------------------------------------

def plotar_violinos_todas_rqs(df: pd.DataFrame):
    """
    Grade 2x3 com violin plots para as metricas principais de cada RQ:
      [0,0] RQ1 - Tempo (s)
      [0,1] RQ2 - Taxa de Sucesso
      [0,2] RQ3 - CC Media
      [1,0] RQ4 - Indice de Manutenibilidade
      [1,1] RQ4 - Densidade CC/SLOC
      [1,2] RQ5 - IDG
    """
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    cores_lista = [COR[t] for t in ORDEM]
    rotulos_lista = [ROTULO[t] for t in ORDEM]

    paineis = [
        ("tempo_segundos",          "Tempo (segundos)",           "RQ1 — Tempo de Resolucao"),
        ("taxa_sucesso",             "Taxa de Sucesso (0-1)",       "RQ2 — Correcao dos Testes"),
        ("cc_media",                 "CC Media",                    "RQ3 — Complexidade Ciclomatica"),
        ("indice_manutenibilidade",  "MI (0-100)",                  "RQ4 — Indice de Manutenibilidade"),
        ("densidade_cc_sloc",        "CC / SLOC",                   "RQ4 — Densidade de Complexidade"),
        ("IDG",                      "IDG (0-1)",                   "RQ5 — Desempenho Global (IDG)"),
    ]

    for ax, (col, ylabel, title) in zip(axes.flat, paineis):
        grupos = [df.loc[df.tratamento == t, col].dropna().values for t in ORDEM]
        violin_ax(ax, grupos, cores_lista, rotulos_lista, ylabel, title)

        # Anotar mediana em cada grupo
        for i, grupo in enumerate(grupos):
            if len(grupo):
                med = np.median(grupo)
                ax.text(i + 0.28, med, f"{med:.2f}",
                        va="center", fontsize=7.5, color=TINTA_2)

    # Legenda global
    itens = [mpatches.Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    fig.legend(handles=itens, loc="lower center", ncol=2,
               frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.0))

    fig.suptitle(
        "Visao Geral — Violin Plots de Todas as RQs (RQ1 a RQ5)",
        x=0.03, ha="left", fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))

    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = GRAFICOS / "rq_violinos.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print(f"grafico gerado: {caminho.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Iniciando analise RQ5 (Indice de Desempenho Global - IDG)...")

    df = carregar_e_calcular(DADOS_CSV)

    # Resumo descritivo
    resumo = calcular_resumo_rq5(df)
    resumo.to_csv(SAIDA_RESUMO_RQ5, index=False)
    print(f"\nResumo descritivo do IDG:\n{resumo.to_string(index=False)}")
    print(f"\nSalvo em: {SAIDA_RESUMO_RQ5.name}")

    # Graficos
    plotar_rq5_idg(df)
    plotar_violinos_todas_rqs(df)

    print("\nAnalise da RQ5 concluida com sucesso!")


if __name__ == "__main__":
    main()

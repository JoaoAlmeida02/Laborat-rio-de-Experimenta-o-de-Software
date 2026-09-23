"""
Analise da RQ4: Indice de Manutenibilidade (MI) e Densidade de Complexidade (CC/SLOC),
considerando tambem o tamanho do codigo produzido.

Mapeia a RQ4 do experimento LAB02:
"O uso de assistente de IA melhora o Indice de Manutenibilidade (MI) e a
Densidade de Complexidade (CC/SLOC), considerando tambem o tamanho do codigo produzido?"

Uso:
    python LAB02/Lab02S03/analise_rq4.py

Gera:
    - resumo_rq4.csv: estatisticas descritivas de MI, CC/SLOC e SLOC por tratamento
    - normalizacao_rq4.csv: valores por trial com densidade normalizada
    - graficos/rq4_mi_densidade.png: paineis de MI pareado, CC/SLOC e CC vs SLOC
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
DADOS_CONSOLIDADOS_CSV = BASE / "dados_consolidados.csv"
GRAFICOS = BASE / "graficos"
SAIDA_RESUMO_RQ4 = BASE / "resumo_rq4.csv"
SAIDA_NORMALIZACAO_RQ4 = BASE / "normalizacao_rq4.csv"

# ---------------------------------------------------------------------------
# Paleta visual (identica aos demais scripts)
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
# Carga e derivacao de metricas
# ---------------------------------------------------------------------------

def carregar_dados() -> pd.DataFrame:
    if not DADOS_CONSOLIDADOS_CSV.exists():
        raise FileNotFoundError(
            f"Arquivo {DADOS_CONSOLIDADOS_CSV} nao encontrado. "
            "Execute o dashboard.py primeiro para gerar o dados_consolidados.csv."
        )

    df = pd.read_csv(DADOS_CONSOLIDADOS_CSV)

    # Metrica derivada: Densidade de Complexidade (variavel central da RQ4)
    df["densidade_cc_sloc"] = df["cc_total"] / df["sloc"].replace(0, np.nan)
    df["densidade_cc_lloc"] = df["cc_total"] / df["lloc"].replace(0, np.nan)

    return df


# ---------------------------------------------------------------------------
# Estatisticas descritivas
# ---------------------------------------------------------------------------

def calcular_estatisticas_rq4(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula mediana, IQR, media, desvio padrao, min e max para as metricas da RQ4."""
    metricas = [
        "indice_manutenibilidade",
        "densidade_cc_sloc",
        "densidade_cc_lloc",
        "sloc",
        "loc",
        "cc_total",
        "cc_media",
    ]

    registros = []
    for m in metricas:
        for t in ORDEM:
            serie = df.loc[df.tratamento == t, m].dropna()
            q1 = serie.quantile(0.25)
            q3 = serie.quantile(0.75)
            registros.append(
                {
                    "metrica": m,
                    "tratamento": t,
                    "n": len(serie),
                    "mediana": round(serie.median(), 3),
                    "q1": round(q1, 3),
                    "q3": round(q3, 3),
                    "iqr": round(q3 - q1, 3),
                    "media": round(serie.mean(), 3),
                    "desvio_padrao": round(serie.std(), 3),
                    "min": round(serie.min(), 3),
                    "max": round(serie.max(), 3),
                }
            )

    return pd.DataFrame(registros)


# ---------------------------------------------------------------------------
# Tabela de normalizacao por trial
# ---------------------------------------------------------------------------

def gerar_tabela_normalizacao(df: pd.DataFrame) -> pd.DataFrame:
    cols_base = [
        "trial_id", "pessoa", "kata", "tratamento",
        "loc", "sloc", "cc_media", "cc_total",
        "densidade_cc_sloc", "densidade_cc_lloc", "indice_manutenibilidade",
    ]
    sub = df[cols_base].copy()
    sub["densidade_cc_sloc"] = sub["densidade_cc_sloc"].round(3)
    sub["densidade_cc_lloc"] = sub["densidade_cc_lloc"].round(3)
    return sub


# ---------------------------------------------------------------------------
# Outliers (criterio 1.5 x IQR)
# ---------------------------------------------------------------------------

def detectar_outliers(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Retorna trials fora da faixa 1.5xIQR, por tratamento. Apenas reportados."""
    rows = []
    for trat, g in df.dropna(subset=[col]).groupby("tratamento"):
        q1, q3 = g[col].quantile(0.25), g[col].quantile(0.75)
        iqr_val = q3 - q1
        lo, hi = q1 - 1.5 * iqr_val, q3 + 1.5 * iqr_val
        mask = (g[col] < lo) | (g[col] > hi)
        for _, r in g[mask].iterrows():
            rows.append(
                dict(
                    trial_id=r["trial_id"],
                    pessoa=r["pessoa"],
                    tratamento=trat,
                    metrica=col,
                    valor=round(r[col], 4),
                    limite_inf=round(lo, 3),
                    limite_sup=round(hi, 3),
                )
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Grafico RQ4
# ---------------------------------------------------------------------------

def plotar_rq4(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    rng = np.random.default_rng(42)

    # -- Painel 1: Indice de Manutenibilidade pareado por pessoa ---------------
    pessoas = sorted(df["pessoa"].unique())
    med = (
        df.groupby(["pessoa", "tratamento"])["indice_manutenibilidade"]
        .median()
        .unstack()
    )
    for y, p in enumerate(pessoas):
        axes[0].hlines(y, med.loc[p].min(), med.loc[p].max(),
                       color=EIXO, lw=3, zorder=1)
        for t in ORDEM:
            axes[0].scatter(
                med.loc[p, t], y,
                s=75, color=COR[t], marker=MARCADOR[p],
                zorder=3, edgecolor=SUPERFICIE, linewidth=1.2,
            )
            axes[0].annotate(
                f"{med.loc[p, t]:.1f}",
                (med.loc[p, t], y),
                textcoords="offset points",
                xytext=(0, 9),
                ha="center",
                fontsize=8,
                color=TINTA_2,
            )
    axes[0].set_yticks(range(len(pessoas)))
    axes[0].set_yticklabels(pessoas)
    axes[0].set_ylim(-0.6, len(pessoas) - 0.4)
    axes[0].invert_yaxis()
    axes[0].set_title("Indice de Manutenibilidade Pareado (MI)")
    axes[0].set_xlabel("MI (0-100, maior = melhor)")
    axes[0].grid(axis="y", visible=False)

    # -- Painel 2: Densidade de Complexidade CC/SLOC ---------------------------
    for i, t in enumerate(ORDEM):
        sub = df[df.tratamento == t]
        q1, med_val, q3 = sub["densidade_cc_sloc"].quantile([0.25, 0.5, 0.75])
        axes[1].vlines(i, q1, q3, color=COR[t], lw=9, alpha=0.3,
                       capstyle="round", zorder=1)
        axes[1].hlines(med_val, i - 0.3, i + 0.3, color=TINTA, lw=2, zorder=2)
        axes[1].text(
            i + 0.34, med_val, f"mediana {med_val:.3f}",
            va="center", fontsize=8, color=TINTA_2,
        )
        desloc = rng.uniform(-0.12, 0.12, len(sub))
        for (_, r), dx in zip(sub.iterrows(), desloc):
            axes[1].scatter(
                i + dx,
                r["densidade_cc_sloc"],
                marker=MARCADOR[r["pessoa"]],
                s=55,
                facecolor=COR[t],
                edgecolor=TINTA,
                linewidth=0.8,
                zorder=3,
            )
    axes[1].set_xticks(range(len(ORDEM)))
    axes[1].set_xticklabels([ROTULO[t] for t in ORDEM], fontsize=10)
    axes[1].set_xlim(-0.6, 1.8)
    axes[1].set_title("Densidade de Complexidade (CC / SLOC)")
    axes[1].set_ylabel("CC total / Linhas de Codigo (SLOC)")
    axes[1].grid(axis="x", visible=False)

    # -- Painel 3: Scatter CC Total x SLOC com linha de tendencia -------------
    for t in ORDEM:
        sub = df[df.tratamento == t]
        for _, r in sub.iterrows():
            axes[2].scatter(
                r["sloc"],
                r["cc_total"],
                marker=MARCADOR[r["pessoa"]],
                s=65,
                facecolor=COR[t],
                edgecolor=TINTA,
                linewidth=0.8,
                zorder=3,
            )
        if len(sub) > 1:
            z = np.polyfit(sub["sloc"], sub["cc_total"], 1)
            p_fn = np.poly1d(z)
            x_vals = np.linspace(sub["sloc"].min(), sub["sloc"].max(), 50)
            axes[2].plot(
                x_vals, p_fn(x_vals),
                color=COR[t], linestyle="--", alpha=0.7, lw=1.5,
                label=f"Tendencia {ROTULO[t]}",
            )
    axes[2].set_title("Complexidade Total (CC) vs Tamanho (SLOC)")
    axes[2].set_xlabel("Linhas de Codigo Fonte (SLOC)")
    axes[2].set_ylabel("Complexidade Ciclomatica Total (CC)")
    axes[2].legend(frameon=False, fontsize=8)

    # -- Legenda global --------------------------------------------------------
    itens = [Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    itens += [
        Line2D([], [], marker=m, color=TINTA_MUDA, linestyle="",
               markersize=7, label=p)
        for p, m in MARCADOR.items()
    ]
    fig.legend(
        handles=itens, loc="lower center", ncol=5,
        frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.0),
    )

    fig.suptitle(
        "RQ4: Indice de Manutenibilidade (MI) e Densidade de Complexidade (CC/SLOC) por Tratamento",
        x=0.03, ha="left", fontsize=12, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))

    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = GRAFICOS / "rq4_mi_densidade.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print(f"grafico gerado: {caminho.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Iniciando analise RQ4 (MI, CC/SLOC e tamanho do codigo)...")

    df = carregar_dados()

    # Outliers (apenas reportados, nao removidos)
    print("\nOutliers detectados (criterio 1.5 x IQR):")
    for col in ["indice_manutenibilidade", "densidade_cc_sloc", "sloc"]:
        out = detectar_outliers(df, col)
        if not out.empty:
            print(out.to_string(index=False))
        else:
            print(f"  {col}: nenhum outlier identificado.")

    # Resumo descritivo
    resumo_df = calcular_estatisticas_rq4(df)
    resumo_df.to_csv(SAIDA_RESUMO_RQ4, index=False)
    print(f"\nResumo descritivo salvo em: {SAIDA_RESUMO_RQ4.name}")

    # Tabela de normalizacao por trial
    norm_df = gerar_tabela_normalizacao(df)
    norm_df.to_csv(SAIDA_NORMALIZACAO_RQ4, index=False)
    print(f"Tabela de normalizacao por trial salva em: {SAIDA_NORMALIZACAO_RQ4.name}")

    # Grafico
    plotar_rq4(df)

    print("\nAnalise da RQ4 concluida com sucesso!")


if __name__ == "__main__":
    main()

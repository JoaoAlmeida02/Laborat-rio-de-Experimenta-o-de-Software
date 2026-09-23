"""
Analise da RQ3: Complexidade Ciclomatica e Duplicacao normalizadas por LOC.

Mapeia a RQ3 do experimento LAB02:
"O uso de assistente de IA altera a complexidade ciclomatica ou a duplicacao do codigo produzido?"
Com as variaveis de controle SLOC/LOC e indice de manutenibilidade (MI).

Uso:
    python LAB02/Lab02S03/analise_rq3.py

Gera:
    - resumo_rq3.csv: metricas descritivas (mediana, IQR, media, desvio padrao, min, max)
    - normalizacao_rq3.csv: densidade de complexidade (CC/SLOC, CC/LLOC) por trial
    - graficos/rq3_densidade_complexidade.png: distribuicao e correlacao de CC vs SLOC
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parent
DADOS_CONSOLIDADOS_CSV = BASE / "dados_consolidados.csv"
GRAFICOS = BASE / "graficos"
SAIDA_RESUMO_RQ3 = BASE / "resumo_rq3.csv"
SAIDA_NORMALIZACAO = BASE / "normalizacao_rq3.csv"

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


def carregar_dados() -> pd.DataFrame:
    if not DADOS_CONSOLIDADOS_CSV.exists():
        raise FileNotFoundError(f"Arquivo {DADOS_CONSOLIDADOS_CSV} nao encontrado. Execute o dashboard.py primeiro.")
    
    df = pd.read_csv(DADOS_CONSOLIDADOS_CSV)
    
    # Metricas derivadas normalizadas por tamanho de codigo (variavel de controle)
    df["densidade_cc_sloc"] = df["cc_total"] / df["sloc"].replace(0, np.nan)
    df["densidade_cc_lloc"] = df["cc_total"] / df["lloc"].replace(0, np.nan)
    df["densidade_cc_media_sloc"] = df["cc_media"] / df["sloc"].replace(0, np.nan)
    
    return df


def calcular_estatisticas_rq3(df: pd.DataFrame) -> pd.DataFrame:
    metricas = [
        "cc_media",
        "cc_max",
        "cc_total",
        "sloc",
        "loc",
        "indice_manutenibilidade",
        "duplicacao_pct",
        "densidade_cc_sloc",
        "densidade_cc_lloc",
    ]
    
    registros = []
    for m in metricas:
        for t in ORDEM:
            serie = df.loc[df.tratamento == t, m].dropna()
            q1 = serie.quantile(0.25)
            q3 = serie.quantile(0.75)
            mediana = serie.median()
            iqr = q3 - q1
            media = serie.mean()
            std = serie.std()
            
            registros.append(
                {
                    "metrica": m,
                    "tratamento": t,
                    "n": len(serie),
                    "mediana": round(mediana, 3),
                    "q1": round(q1, 3),
                    "q3": round(q3, 3),
                    "iqr": round(iqr, 3),
                    "media": round(media, 3),
                    "desvio_padrao": round(std, 3),
                    "min": round(serie.min(), 3),
                    "max": round(serie.max(), 3),
                }
            )
            
    return pd.DataFrame(registros)


def gerar_tabela_normalizacao(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "trial_id",
        "pessoa",
        "kata",
        "tratamento",
        "loc",
        "sloc",
        "cc_media",
        "cc_total",
        "densidade_cc_sloc",
        "indice_manutenibilidade",
        "duplicacao_pct",
    ]
    sub = df[cols].copy()
    sub["densidade_cc_sloc"] = sub["densidade_cc_sloc"].round(3)
    return sub


def plotar_rq3_normalizada(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    
    # Painel 1: Densidade de Complexidade (CC Total / SLOC)
    rng = np.random.default_rng(42)
    for i, t in enumerate(ORDEM):
        sub = df[df.tratamento == t]
        q1, med, q3 = sub["densidade_cc_sloc"].quantile([0.25, 0.5, 0.75])
        axes[0].vlines(i, q1, q3, color=COR[t], lw=9, alpha=0.3, capstyle="round", zorder=1)
        axes[0].hlines(med, i - 0.3, i + 0.3, color=TINTA, lw=2, zorder=2)
        axes[0].text(i + 0.34, med, f"mediana {med:.2f}", va="center", fontsize=8, color=TINTA_2)
        
        desloc = rng.uniform(-0.12, 0.12, len(sub))
        for (_, r), dx in zip(sub.iterrows(), desloc):
            axes[0].scatter(
                i + dx,
                r["densidade_cc_sloc"],
                marker=MARCADOR[r["pessoa"]],
                s=55,
                facecolor=COR[t],
                edgecolor=TINTA,
                linewidth=0.8,
                zorder=3,
            )
            
    axes[0].set_xticks(range(len(ORDEM)))
    axes[0].set_xticklabels([ROTULO[t] for t in ORDEM], fontsize=10)
    axes[0].set_xlim(-0.6, 1.8)
    axes[0].set_title("Densidade de Complexidade (CC / SLOC)")
    axes[0].set_ylabel("CC / Linha de Codigo (SLOC)")
    axes[0].grid(axis="x", visible=False)

    # Painel 2: Scatter plot CC Total vs SLOC
    for t in ORDEM:
        sub = df[df.tratamento == t]
        for _, r in sub.iterrows():
            axes[1].scatter(
                r["sloc"],
                r["cc_total"],
                marker=MARCADOR[r["pessoa"]],
                s=65,
                facecolor=COR[t],
                edgecolor=TINTA,
                linewidth=0.8,
                zorder=3,
            )
            
    # Linha de tendencia para ilustrar normalizacao
    for t in ORDEM:
        sub = df[df.tratamento == t]
        if len(sub) > 1:
            z = np.polyfit(sub["sloc"], sub["cc_total"], 1)
            p = np.poly1d(z)
            x_vals = np.linspace(sub["sloc"].min(), sub["sloc"].max(), 50)
            axes[1].plot(x_vals, p(x_vals), color=COR[t], linestyle="--", alpha=0.7, lw=1.5, label=f"Tendencia {ROTULO[t]}")
            
    axes[1].set_title("Complexidade (CC Total) vs Tamanho (SLOC)")
    axes[1].set_xlabel("Linhas de Codigo Fonte (SLOC)")
    axes[1].set_ylabel("Complexidade Ciclomatica Total")
    axes[1].legend(frameon=False, fontsize=8)

    # Painel 3: Indice de Manutenibilidade Normalizado por Pessoa
    pessoas = sorted(df["pessoa"].unique())
    med = df.groupby(["pessoa", "tratamento"])["indice_manutenibilidade"].median().unstack()
    for y, p in enumerate(pessoas):
        axes[2].hlines(y, med.loc[p].min(), med.loc[p].max(), color=EIXO, lw=3, zorder=1)
        for t in ORDEM:
            axes[2].scatter(med.loc[p, t], y, s=70, color=COR[t], marker=MARCADOR[p], zorder=3, edgecolor=SUPERFICIE, linewidth=1.2)
            axes[2].annotate(
                f"{med.loc[p, t]:.1f}",
                (med.loc[p, t], y),
                textcoords="offset points",
                xytext=(0, 9),
                ha="center",
                fontsize=8,
                color=TINTA_2,
            )
    axes[2].set_yticks(range(len(pessoas)))
    axes[2].set_yticklabels(pessoas)
    axes[2].set_ylim(-0.6, len(pessoas) - 0.4)
    axes[2].invert_yaxis()
    axes[2].set_title("Indice de Manutenibilidade Pareado (MI)")
    axes[2].set_xlabel("MI (0-100, maior = melhor)")
    axes[2].grid(axis="y", visible=False)

    # Legenda global
    itens = [Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    itens += [
        Line2D([], [], marker=m, color=TINTA_MUDA, linestyle="", markersize=7, label=p) for p, m in MARCADOR.items()
    ]
    fig.legend(handles=itens, loc="lower center", ncol=5, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.0))

    fig.suptitle("RQ3 Detalhada: Complexidade Ciclomatica, Duplicacao e Manutenibilidade Normalizadas por LOC", x=0.03, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho_grafico = GRAFICOS / "rq3_densidade_complexidade.png"
    fig.savefig(caminho_grafico, dpi=160)
    plt.close(fig)
    print("grafico gerado:", caminho_grafico.name)


def main():
    print("Iniciando analise RQ3 (complexidade e duplicacao normalizadas por LOC)...")
    df = carregar_dados()
    
    resumo_df = calcular_estatisticas_rq3(df)
    resumo_df.to_csv(SAIDA_RESUMO_RQ3, index=False)
    print(f"Resumo descritivo salvo em: {SAIDA_RESUMO_RQ3.name}")
    
    norm_df = gerar_tabela_normalizacao(df)
    norm_df.to_csv(SAIDA_NORMALIZACAO, index=False)
    print(f"Tabela de normalizacao por trial salva em: {SAIDA_NORMALIZACAO.name}")
    
    plotar_rq3_normalizada(df)
    print("Analise da RQ3 concluida com sucesso!")


if __name__ == "__main__":
    main()

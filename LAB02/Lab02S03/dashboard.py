"""
Dashboard de visualizacao do experimento LAB02 (Sprint 03, Passo 6).

Le resultados.csv (cronometro.py) e metrics.csv (collect_metrics.py), junta pelo
trial_id e gera graficos comparando os tratamentos com IA e sem IA.

Uso (a partir de qualquer pasta):
    python LAB02/Lab02S03/dashboard.py

Saidas em Lab02S03/:
    dados_consolidados.csv    resultados + metricas, 1 linha por trial
    resumo_descritivo.csv     mediana, Q1, Q3 e n por metrica e tratamento
    graficos/*.png            graficos individuais e dashboard.png (visao geral)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

BASE = Path(__file__).resolve().parent
S01 = BASE.parent / "Lab02S01"
RESULTADOS_CSV = S01 / "dados" / "resultados.csv"
METRICS_CSV = S01 / "metrics.csv"
SAIDA_DADOS = BASE / "dados_consolidados.csv"
SAIDA_RESUMO = BASE / "resumo_descritivo.csv"
GRAFICOS = BASE / "graficos"

ORDEM = ["sem_ia", "com_ia"]
ROTULO = {"sem_ia": "Sem IA", "com_ia": "Com IA"}
COR = {"sem_ia": "#eb6834", "com_ia": "#2a78d6"}
MARCADOR = {"Joao": "o", "Lucas": "s", "Vitor": "^"}
KATAS = {
    "kata1_validador_cofre": "Kata 1\nValidador de cofre",
    "kata2_rota_entregador": "Kata 2\nRota do entregador",
    "kata3_compressor_log": "Kata 3\nCompressor de log",
    "kata4_escalonador_plantao": "Kata 4\nEscalonador de plantao",
}

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


def carregar() -> pd.DataFrame:
    res = pd.read_csv(RESULTADOS_CSV)
    met = pd.read_csv(METRICS_CSV)
    met = met.drop(columns=["kata", "participante", "tratamento"])
    df = res.merge(met, on="trial_id", how="inner", validate="one_to_one")
    if len(df) != len(res):
        faltando = sorted(set(res.trial_id) - set(df.trial_id))
        raise SystemExit(f"Trials sem metricas em metrics.csv (rode collect_metrics.py): {faltando}")
    df["taxa_sucesso"] = 100 * df["testes_passando"] / df["testes_total"]
    df["completo"] = df["testes_passando"] == df["testes_total"]
    df = df.rename(columns={"pessoa": "pessoa"})
    return df


def resumo(df: pd.DataFrame) -> pd.DataFrame:
    metricas = ["tempo_segundos", "taxa_sucesso", "cc_media", "sloc", "indice_manutenibilidade", "duplicacao_pct"]
    linhas = []
    for m in metricas:
        for t in ORDEM:
            v = df.loc[df.tratamento == t, m]
            linhas.append(
                {
                    "metrica": m,
                    "tratamento": t,
                    "n": len(v),
                    "mediana": v.median(),
                    "q1": v.quantile(0.25),
                    "q3": v.quantile(0.75),
                    "iqr": v.quantile(0.75) - v.quantile(0.25),
                }
            )
    return pd.DataFrame(linhas).round(2)


def _deslocamentos(n: int, largura: float = 0.2) -> np.ndarray:
    if n == 1:
        return np.array([0.0])
    return np.linspace(-largura, largura, n)


def painel_distribuicao(ax, df, col, titulo, ylabel, log=False, ylim=None, marcar_incompletos=False, fmt="{:.0f}", rotular_mediana=True):
    rng = np.random.default_rng(7)
    for i, t in enumerate(ORDEM):
        sub = df[df.tratamento == t]
        q1, med, q3 = sub[col].quantile([0.25, 0.5, 0.75])
        ax.vlines(i, q1, q3, color=COR[t], lw=9, alpha=0.3, capstyle="round", zorder=1)
        ax.hlines(med, i - 0.3, i + 0.3, color=TINTA, lw=2, zorder=2)
        if rotular_mediana:
            ax.text(i + 0.34, med, "mediana " + fmt.format(med), va="center", fontsize=8, color=TINTA_2)
        desloc = rng.permutation(_deslocamentos(len(sub)))
        for (_, r), dx in zip(sub.iterrows(), desloc):
            cheio = (not marcar_incompletos) or r["completo"]
            ax.scatter(
                i + dx,
                r[col],
                marker=MARCADOR[r["pessoa"]],
                s=52,
                facecolor=COR[t] if cheio else SUPERFICIE,
                edgecolor=COR[t],
                linewidth=1.7,
                zorder=3,
            )
    ax.set_xticks(range(len(ORDEM)))
    ax.set_xticklabels([ROTULO[t] for t in ORDEM], fontsize=10)
    ax.set_xlim(-0.6, 1.9)
    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    if log:
        ax.set_yscale("log")
        ticks = [t for t in [2, 5, 10, 30, 60, 120, 300, 600] if ylim is None or ylim[0] <= t <= ylim[1]]
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks])
        ax.minorticks_off()
    if ylim:
        ax.set_ylim(*ylim)


def painel_duplicacao(ax, df):
    painel_distribuicao(ax, df, "duplicacao_pct", "Duplicacao de codigo", "% de linhas duplicadas", ylim=(-0.5, 5), fmt="{:.1f}%", rotular_mediana=not (df["duplicacao_pct"] == 0).all())
    if (df["duplicacao_pct"] == 0).all():
        ax.text(0.5, 0.5, "0% em todos os trials", transform=ax.transAxes, ha="center", fontsize=8.5, color=TINTA_2)


def painel_pareado(ax, df, col, titulo, xlabel, log=False, xlim=None, fmt="{:.0f}"):
    pessoas = sorted(df["pessoa"].unique())
    med = df.groupby(["pessoa", "tratamento"])[col].median().unstack()
    for y, p in enumerate(pessoas):
        ax.hlines(y, med.loc[p].min(), med.loc[p].max(), color=EIXO, lw=3, zorder=1)
        for t in ORDEM:
            ax.scatter(med.loc[p, t], y, s=70, color=COR[t], marker=MARCADOR[p], zorder=3, edgecolor=SUPERFICIE, linewidth=1.2)
        for t in ORDEM:
            ax.annotate(
                fmt.format(med.loc[p, t]),
                (med.loc[p, t], y),
                textcoords="offset points",
                xytext=(0, 9),
                ha="center",
                fontsize=8,
                color=TINTA_2,
            )
    ax.set_yticks(range(len(pessoas)))
    ax.set_yticklabels(pessoas)
    ax.set_ylim(-0.6, len(pessoas) - 0.4)
    ax.invert_yaxis()
    ax.set_title(titulo)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)
    if log:
        ax.set_xscale("log")
        ax.minorticks_off()
        ticks = [5, 10, 30, 60, 120, 300]
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks])
    if xlim:
        ax.set_xlim(*xlim)


def painel_por_kata(ax, df):
    for i, k in enumerate(KATAS):
        for t, dx in (("sem_ia", -0.13), ("com_ia", 0.13)):
            sub = df[(df.kata == k) & (df.tratamento == t)]
            for (_, r), off in zip(sub.iterrows(), _deslocamentos(len(sub), 0.05)):
                ax.scatter(
                    i + dx + off,
                    r["tempo_segundos"],
                    marker=MARCADOR[r["pessoa"]],
                    s=55,
                    facecolor=COR[t] if r["completo"] else SUPERFICIE,
                    edgecolor=COR[t],
                    linewidth=1.7,
                    zorder=3,
                )
    ax.set_yscale("log")
    ticks = [5, 10, 30, 60, 120, 300, 600]
    ax.set_yticks(ticks)
    ax.set_yticklabels([str(t) for t in ticks])
    ax.minorticks_off()
    ax.set_ylim(2, 700)
    ax.set_xticks(range(len(KATAS)))
    ax.set_xticklabels(list(KATAS.values()), fontsize=8.5)
    ax.set_xlim(-0.6, len(KATAS) - 0.4)
    ax.set_ylabel("segundos (escala log)")
    ax.set_title("Tempo por kata e tratamento")
    ax.grid(axis="x", visible=False)


def legenda(fig, incompletos=True, y=0.0):
    itens = [Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    itens += [
        Line2D([], [], marker=m, color=TINTA_MUDA, linestyle="", markersize=7, label=p) for p, m in MARCADOR.items()
    ]
    if incompletos:
        itens += [
            Line2D([], [], marker="o", markerfacecolor=TINTA_MUDA, markeredgecolor=TINTA_MUDA, linestyle="", markersize=7, label="passou todos os testes"),
            Line2D([], [], marker="o", markerfacecolor=SUPERFICIE, markeredgecolor=TINTA_MUDA, linestyle="", markersize=7, label="falhou algum teste"),
        ]
    fig.legend(handles=itens, loc="lower center", ncol=len(itens) if fig.get_figwidth() > 9 else 4, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, y))


def salvar(fig, nome):
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = GRAFICOS / nome
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print("gerado:", caminho.relative_to(BASE.parent.parent))


def painel_tempo(ax, df):
    painel_distribuicao(
        ax, df, "tempo_segundos", "Tempo ate encerrar o trial", "segundos (escala log)",
        log=True, ylim=(2, 700), marcar_incompletos=True,
    )


def painel_sucesso(ax, df):
    painel_distribuicao(
        ax, df, "taxa_sucesso", "Taxa de sucesso nos testes", "% de testes passando",
        ylim=(0, 108), fmt="{:.0f}%",
    )
    ax.set_yticks([0, 25, 50, 75, 100])


def painel_cc(ax, df):
    painel_distribuicao(ax, df, "cc_media", "Complexidade ciclomatica", "CC media por funcao", ylim=(0, 14), fmt="{:.1f}")


def painel_sloc(ax, df):
    painel_distribuicao(ax, df, "sloc", "Tamanho (controle)", "SLOC", ylim=(0, 36), fmt="{:.0f}")


def painel_mi(ax, df):
    painel_distribuicao(ax, df, "indice_manutenibilidade", "Indice de manutenibilidade", "MI (0-100, maior = melhor)", ylim=(40, 100), fmt="{:.0f}")


def grafico_tempo(df):
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    painel_tempo(ax, df)
    fig.suptitle("RQ1 - Tempo por tratamento", x=0.06, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.915, "barra = intervalo interquartil, traco = mediana; n = 6 trials por tratamento", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    legenda(fig)
    salvar(fig, "01_tempo.png")


def grafico_sucesso(df):
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    painel_sucesso(ax, df)
    fig.suptitle("RQ2 - Taxa de sucesso por tratamento", x=0.06, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.915, "testes de aceitacao passando ao final do trial; n = 6 por tratamento", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    legenda(fig, incompletos=False)
    salvar(fig, "02_taxa_sucesso.png")


def grafico_metricas(df):
    fig, axes = plt.subplots(1, 4, figsize=(15, 5))
    painel_cc(axes[0], df)
    painel_sloc(axes[1], df)
    painel_mi(axes[2], df)
    painel_duplicacao(axes[3], df)
    fig.suptitle("RQ3 - Estrutura do codigo por tratamento", x=0.03, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.03, 0.915, "SLOC entra como variavel de controle: complexidade e duplicacao devem ser lidas junto com o tamanho do codigo", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    legenda(fig, incompletos=False)
    salvar(fig, "03_metricas_estaticas.png")


def grafico_pareado(df):
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.9))
    painel_pareado(axes[0], df, "tempo_segundos", "Tempo mediano", "segundos (escala log)", log=True, xlim=(2.5, 500))
    painel_pareado(axes[1], df, "taxa_sucesso", "Taxa de sucesso mediana", "% de testes passando", xlim=(70, 105), fmt="{:.0f}%")
    painel_pareado(axes[2], df, "cc_media", "Complexidade ciclomatica mediana", "CC media por funcao", xlim=(3, 13), fmt="{:.1f}")
    fig.suptitle("Comparacao dentro de cada pessoa (desenho within-subject)", x=0.03, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.03, 0.895, "mediana dos 2 trials de cada pessoa em cada tratamento (n = 3 pares)", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.1, 1, 0.88))
    legenda(fig, incompletos=False)
    salvar(fig, "04_pareado_por_pessoa.png")


def grafico_kata(df):
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    painel_por_kata(ax, df)
    fig.suptitle("Tempo por kata: cada kata foi resolvido por 3 pessoas", x=0.06, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.06, 0.915, "ajuda a separar o efeito da IA da dificuldade de cada kata", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    legenda(fig)
    salvar(fig, "05_tempo_por_kata.png")


def dashboard(df):
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9.6))
    painel_tempo(axes[0, 0], df)
    painel_sucesso(axes[0, 1], df)
    painel_pareado(axes[0, 2], df, "tempo_segundos", "Tempo mediano por pessoa", "segundos (escala log)", log=True, xlim=(2.5, 500))
    painel_cc(axes[1, 0], df)
    painel_sloc(axes[1, 1], df)
    painel_mi(axes[1, 2], df)
    fig.suptitle("LAB02 - Assistente de IA vs. codificacao manual", x=0.03, ha="left", fontsize=15, fontweight="bold")
    dup = "duplicacao de codigo: 0% em todos os trials; " if (df["duplicacao_pct"] == 0).all() else ""
    n_cens = int(df["censurado"].sum())
    cens = "nenhum atingiu o time-box de 35 min" if n_cens == 0 else f"{n_cens} atingiram o time-box de 35 min"
    fig.text(
        0.03, 0.937,
        f"{len(df)} trials (3 integrantes x 4 katas), {cens}; {dup}barra = IQR, traco = mediana",
        fontsize=9, color=TINTA_2,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    legenda(fig)
    salvar(fig, "dashboard.png")


def main():
    df = carregar()
    df.to_csv(SAIDA_DADOS, index=False)
    resumo(df).to_csv(SAIDA_RESUMO, index=False)
    print(f"{len(df)} trials consolidados em {SAIDA_DADOS.name}; resumo em {SAIDA_RESUMO.name}")
    grafico_tempo(df)
    grafico_sucesso(df)
    grafico_metricas(df)
    grafico_pareado(df)
    grafico_kata(df)
    dashboard(df)


if __name__ == "__main__":
    main()

"""
analise_rq1_rq2.py
==================
Sprint 03 - Issue #32 - LAB02
Teste estatistico de Wilcoxon para:
  RQ1: Tempo de resolucao (tempo_segundos)
  RQ2: Taxa de sucesso nos testes (testes_passando / testes_total)

Fonte : LAB02/Lab02S01/dados/resultados.csv
Saida : console + LAB02/Lab02S03/resultados_rq1_rq2.md
"""

import warnings
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.stats import wilcoxon

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
THIS_DIR = Path(__file__).parent.resolve()
CSV_PATH = THIS_DIR.parent / "Lab02S01" / "dados" / "resultados.csv"
MD_PATH  = THIS_DIR / "resultados_rq1_rq2.md"
GRAFICOS = THIS_DIR / "graficos"

SEP = "=" * 68

# ── Estilo visual idêntico ao dashboard.py ──────────────────────────────────
ORDEM   = ["sem_ia", "com_ia"]
ROTULO  = {"sem_ia": "Sem IA", "com_ia": "Com IA"}
COR     = {"sem_ia": "#eb6834", "com_ia": "#2a78d6"}
MARCADOR = {"Joao": "o", "Lucas": "s", "Vitor": "^"}

SUPERFICIE = "#fcfcfb"
TINTA      = "#0b0b0b"
TINTA_2    = "#52514e"
TINTA_MUDA = "#898781"
GRADE      = "#e1e0d9"
EIXO       = "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor":   SUPERFICIE,
    "axes.facecolor":     SUPERFICIE,
    "savefig.facecolor":  SUPERFICIE,
    "axes.edgecolor":     EIXO,
    "axes.labelcolor":    TINTA_2,
    "axes.titlecolor":    TINTA,
    "axes.titlesize":     11,
    "axes.titleweight":   "bold",
    "axes.titlelocation": "left",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "axes.axisbelow":     True,
    "grid.color":         GRADE,
    "grid.linewidth":     0.8,
    "xtick.color":        TINTA_MUDA,
    "ytick.color":        TINTA_MUDA,
    "xtick.labelcolor":   TINTA_2,
    "ytick.labelcolor":   TINTA_2,
    "text.color":         TINTA,
    "font.size":          9.5,
})


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def calc_iqr(s: pd.Series) -> float:
    return float(s.quantile(0.75) - s.quantile(0.25))


def detectar_outliers(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Retorna DataFrame com os trials fora da faixa 1.5xIQR, por tratamento."""
    rows = []
    for trat, g in df.dropna(subset=[col]).groupby("tratamento"):
        q1, q3 = g[col].quantile(0.25), g[col].quantile(0.75)
        iqr_val = q3 - q1
        lo, hi = q1 - 1.5 * iqr_val, q3 + 1.5 * iqr_val
        mask = (g[col] < lo) | (g[col] > hi)
        for _, r in g[mask].iterrows():
            rows.append(dict(
                trial_id=r["trial_id"], pessoa=r["pessoa"],
                tratamento=trat, valor=round(r[col], 4),
                limite_inf=round(lo, 3), limite_sup=round(hi, 3),
                censurado=bool(r.get("censurado", False)),
            ))
    return pd.DataFrame(rows)


def pares_por_pessoa(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Mediana de 'col' por (pessoa, tratamento) -> DataFrame com colunas com_ia / sem_ia."""
    agg = (
        df.dropna(subset=[col])
        .groupby(["pessoa", "tratamento"])[col]
        .median()
        .unstack("tratamento")
        .reset_index()
    )
    for t in ["com_ia", "sem_ia"]:
        if t not in agg.columns:
            agg[t] = np.nan
    agg["delta"] = agg["com_ia"] - agg["sem_ia"]
    return agg[["pessoa", "com_ia", "sem_ia", "delta"]].copy()


def rodar_wilcoxon(pares: pd.DataFrame, label: str):
    """Wilcoxon pareado; retorna (stat, pval, n) ou (None, None, n)."""
    x = pares["com_ia"].dropna().values
    y = pares["sem_ia"].dropna().values
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    if n < 2:
        return None, None, n
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        stat, pval = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
        for w in ws:
            print(f"  [scipy] {w.message}")
    return float(stat), float(pval), n


def fmt_wilcoxon_bloco(stat, pval, n, label: str) -> str:
    sig = "SIM  (p < 0.05)" if pval < 0.05 else "NAO  (p >= 0.05)"
    return (
        f"  W = {stat:.1f}   p-valor = {pval:.4f}\n"
        f"  Significativo (alpha=0.05)? {sig}\n"
        f"  ATENCAO: N={n} pares e insuficiente para poder estatistico robusto.\n"
        f"  O teste de Wilcoxon requer N >= 6 para efeitos moderados.\n"
        f"  Interprete {label} como resultado EXPLORATORIO."
    )


# ---------------------------------------------------------------------------
# Carga e pre-processamento
# ---------------------------------------------------------------------------

def carregar_dados(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["tempo_segundos"]  = pd.to_numeric(df["tempo_segundos"],  errors="coerce")
    df["testes_passando"] = pd.to_numeric(df["testes_passando"], errors="coerce")
    df["testes_total"]    = pd.to_numeric(df["testes_total"],    errors="coerce")
    df["censurado"] = df["censurado"].astype(str).str.strip().str.lower() == "true"
    return df.dropna(subset=["trial_id"]).reset_index(drop=True)


def adicionar_taxa_sucesso(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula taxa_sucesso; marca NaN e avisa se testes_total == 0."""
    taxas, avisos = [], []
    for _, r in df.iterrows():
        tot = r["testes_total"]
        if pd.isna(tot) or tot == 0:
            avisos.append(r["trial_id"])
            taxas.append(np.nan)
        else:
            taxas.append(r["testes_passando"] / tot)
    df = df.copy()
    df["taxa_sucesso"] = taxas
    if avisos:
        print(f"  AVISO: testes_total=0 ou ausente em: {avisos}")
        print("         Esses trials serao pulados no calculo de RQ2.")
    return df


# ---------------------------------------------------------------------------
# Relatorio Markdown
# ---------------------------------------------------------------------------

def gerar_markdown(df, pares_rq1, pares_rq2):
    lines = []
    L = lines.append

    L("# Analise Estatistica - RQ1 e RQ2\n\n")
    L("**Sprint 03 - Issue #32 - LAB02**  \n")
    L(f"Fonte: `LAB02/Lab02S01/dados/resultados.csv`  \n")
    L(f"Total de trials: {len(df)}  \n\n")

    n_cens = int(df["censurado"].sum())
    if n_cens:
        ids = df.loc[df["censurado"], "trial_id"].tolist()
        L(f"> **Trials censurados (time-box 35 min):** {n_cens} - {ids}  \n\n")
    else:
        L("> **Trials censurados:** nenhum  \n\n")

    # ── 1. Descritiva ──────────────────────────────────────────────────────
    L("## 1. Analise Descritiva\n\n")
    L("Mediana e IQR por tratamento (todos os 12 trials, sem agregacao previa).\n\n")

    for col, label, fmt in [
        ("tempo_segundos", "RQ1 - Tempo (segundos)", ".1f"),
        ("taxa_sucesso",   "RQ2 - Taxa de Sucesso", ".1%"),
    ]:
        L(f"### {label}\n\n")
        L("| Tratamento | N | Mediana | IQR | Min | Max |\n")
        L("|------------|---|---------|-----|-----|-----|\n")
        for trat, g in df.dropna(subset=[col]).groupby("tratamento"):
            s = g[col]
            L(f"| {trat} | {len(s)} | {s.median():{fmt}} | {calc_iqr(s):{fmt}} "
              f"| {s.min():{fmt}} | {s.max():{fmt}} |\n")
        L("\n")

    # ── 2. Outliers ────────────────────────────────────────────────────────
    L("## 2. Outliers (1.5xIQR por tratamento)\n\n")
    L("Apenas reportados - **nao removidos**.\n\n")

    for col, label in [("tempo_segundos", "RQ1 - Tempo (s)"),
                       ("taxa_sucesso",   "RQ2 - Taxa de Sucesso")]:
        L(f"### {label}\n\n")
        out = detectar_outliers(df, col)
        if out.empty:
            L("Nenhum outlier identificado.\n\n")
        else:
            L("| trial_id | tratamento | valor | faixa valida | censurado |\n")
            L("|----------|------------|-------|--------------|-----------|\n")
            for _, r in out.iterrows():
                flag = "**CENSURADO**" if r["censurado"] else "-"
                L(f"| {r['trial_id']} | {r['tratamento']} | {r['valor']} "
                  f"| [{r['limite_inf']}, {r['limite_sup']}] | {flag} |\n")
            L("\n")

    # ── 3. Pares ───────────────────────────────────────────────────────────
    L("## 3. Pares por Participante\n\n")
    L("Cada participante contribui com 1 par: mediana `com_ia` vs mediana `sem_ia`.\n\n")

    for pares, label, fmt in [
        (pares_rq1, "RQ1 - Tempo (s)", ".1f"),
        (pares_rq2, "RQ2 - Taxa de Sucesso", ".1%"),
    ]:
        L(f"### {label}\n\n")
        L("| Pessoa | com_ia | sem_ia | delta (com - sem) |\n")
        L("|--------|--------|--------|-------------------|\n")
        for _, r in pares.iterrows():
            L(f"| {r['pessoa']} | {r['com_ia']:{fmt}} | {r['sem_ia']:{fmt}} "
              f"| {r['delta']:+{fmt}} |\n")
        L("\n")

    # ── 4. Wilcoxon ────────────────────────────────────────────────────────
    L("## 4. Testes de Wilcoxon (pareado)\n\n")
    L("> **ATENCAO:** N=3 pares. Resultado **exploratorio** - poder estatistico baixo.\n\n")

    for pares, label in [(pares_rq1, "RQ1 - Tempo"), (pares_rq2, "RQ2 - Taxa de Sucesso")]:
        stat, pval, n = rodar_wilcoxon(pares, label)
        L(f"### {label}\n\n")
        if stat is None:
            L(f"Pares insuficientes (N={n}).\n\n")
        else:
            sig = "**Sim** (p < 0.05)" if pval < 0.05 else "**Nao** (p >= 0.05)"
            L("| Parametro | Valor |\n")
            L("|-----------|-------|\n")
            L(f"| N pares | {n} |\n")
            L(f"| Estatistica W | {stat:.1f} |\n")
            L(f"| p-valor (bicaudal) | {pval:.4f} |\n")
            L(f"| Significativo (alfa=0.05)? | {sig} |\n\n")

    # ── 5. Interpretacao ───────────────────────────────────────────────────
    L("## 5. Interpretacao e Limitacoes\n\n")
    L(textwrap.dedent("""\
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
    """))

    MD_PATH.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    buf_md = []

    def p(text=""):
        print(text)
        buf_md.append(text + "\n")

    print(SEP)
    print("  ANALISE RQ1 e RQ2 - Sprint 03 / LAB02")
    print(SEP)

    # Carga
    print(f"\nCarregando: {CSV_PATH}")
    if not CSV_PATH.exists():
        print(f"  ERRO: arquivo nao encontrado em {CSV_PATH}")
        return
    df = carregar_dados(CSV_PATH)
    print(f"  {len(df)} trials carregados.")

    n_cens = int(df["censurado"].sum())
    print(f"  Trials censurados (time-box 35 min): {n_cens}")
    if n_cens:
        print(f"  -> {df.loc[df['censurado'], 'trial_id'].tolist()}")

    # Taxa de sucesso
    print(f"\n{SEP}")
    print("  PRE-PROCESSAMENTO - Taxa de Sucesso (RQ2)")
    print(SEP)
    df = adicionar_taxa_sucesso(df)

    # ── Descritiva ──────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  ANALISE DESCRITIVA")
    print(SEP)

    for col, label in [("tempo_segundos", "RQ1 - Tempo (s)"),
                       ("taxa_sucesso",   "RQ2 - Taxa de Sucesso")]:
        print(f"\n{label}")
        fmt = ".1f" if col == "tempo_segundos" else ".1%"
        rows = []
        for trat, g in df.dropna(subset=[col]).groupby("tratamento"):
            s = g[col]
            rows.append(dict(
                tratamento=trat, N=len(s),
                mediana=f"{s.median():{fmt}}",
                IQR=f"{calc_iqr(s):{fmt}}",
                min=f"{s.min():{fmt}}",
                max=f"{s.max():{fmt}}",
            ))
        print(pd.DataFrame(rows).to_string(index=False))

    # ── Outliers ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  OUTLIERS (1.5xIQR por tratamento)")
    print(SEP)

    for col, label in [("tempo_segundos", "RQ1 - Tempo (s)"),
                       ("taxa_sucesso",   "RQ2 - Taxa de Sucesso")]:
        print(f"\n{label}:")
        out = detectar_outliers(df, col)
        if out.empty:
            print("  Nenhum outlier identificado.")
        else:
            for _, r in out.iterrows():
                flag = " <- CENSURADO (esperado)" if r["censurado"] else ""
                print(f"  * {r['trial_id']}  [{r['tratamento']}]"
                      f"  valor={r['valor']}"
                      f"  faixa=[{r['limite_inf']}, {r['limite_sup']}]{flag}")

    # ── Pares ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  PARES POR PARTICIPANTE")
    print(SEP)

    pares_rq1 = pares_por_pessoa(df, "tempo_segundos")
    pares_rq2 = pares_por_pessoa(df, "taxa_sucesso")

    print("\nRQ1 - Tempo (s)  [mediana por tratamento, por pessoa]")
    print(pares_rq1.rename(columns={"delta": "delta_com-sem"}).to_string(index=False))

    print("\nRQ2 - Taxa de Sucesso  [mediana por tratamento, por pessoa]")
    pares_rq2_disp = pares_rq2.copy()
    pares_rq2_disp["com_ia"]  = pares_rq2_disp["com_ia"].map(lambda x: f"{x:.1%}")
    pares_rq2_disp["sem_ia"]  = pares_rq2_disp["sem_ia"].map(lambda x: f"{x:.1%}")
    pares_rq2_disp["delta"]   = pares_rq2_disp["delta"].map(lambda x: f"{x:+.1%}")
    pares_rq2_disp = pares_rq2_disp.rename(columns={"delta": "delta_com-sem"})
    print(pares_rq2_disp.to_string(index=False))

    # ── Wilcoxon ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  TESTES DE WILCOXON (pareado por participante)")
    print(SEP)

    for pares, label in [(pares_rq1, "RQ1 - Tempo"),
                         (pares_rq2, "RQ2 - Taxa de Sucesso")]:
        print(f"\n{label}:")
        stat, pval, n = rodar_wilcoxon(pares, label)
        if stat is not None:
            print(fmt_wilcoxon_bloco(stat, pval, n, label))
        else:
            print(f"  Pares insuficientes (N={n}).")

    # ── Interpretacao ────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  INTERPRETACAO")
    print(SEP)
    print(textwrap.dedent("""
  Com N=3 pares o Wilcoxon tem poder ~20% para efeitos moderados.
  Um p-valor alto NAO significa ausencia de efeito.
  Um p-valor baixo pode ser fortuito neste tamanho amostral.
  Os indicadores descritivos (mediana, direcao dos pares) sao
  mais informativos do que o p-valor aqui.
  Recomendacao: >= 6 participantes em estudos futuros.
    """).strip())

    print(f"\n{SEP}")
    print("  FIM")
    print(SEP)

    # Gera Markdown
    gerar_markdown(df, pares_rq1, pares_rq2)
    print(f"\nRelatorio salvo em: {MD_PATH}")

    # Gera graficos
    gerar_graficos(df, pares_rq1, pares_rq2)



# ---------------------------------------------------------------------------
# Graficos (mesmo estilo que dashboard.py / analise_rq3.py)
# ---------------------------------------------------------------------------

def _salvar(fig, nome: str):
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    caminho = GRAFICOS / nome
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    print(f"  grafico gerado: graficos/{nome}")


def _legenda(fig, y=0.0):
    itens  = [Patch(facecolor=COR[t], label=ROTULO[t]) for t in ORDEM]
    itens += [Line2D([], [], marker=m, color=TINTA_MUDA, linestyle="",
                     markersize=7, label=p) for p, m in MARCADOR.items()]
    fig.legend(handles=itens, loc="lower center", ncol=len(itens),
               frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, y))


def _painel_distribuicao(ax, df, col, titulo, ylabel, log=False, ylim=None, fmt="{:.0f}"):
    """Strip-plot com barra IQR e traco de mediana."""
    rng = np.random.default_rng(7)
    pessoas = df["pessoa"].unique() if "pessoa" in df.columns else []
    for i, t in enumerate(ORDEM):
        sub = df[df["tratamento"] == t].dropna(subset=[col])
        q1, med, q3 = sub[col].quantile([0.25, 0.5, 0.75])
        ax.vlines(i, q1, q3, color=COR[t], lw=9, alpha=0.3, capstyle="round", zorder=1)
        ax.hlines(med, i - 0.3, i + 0.3, color=TINTA, lw=2, zorder=2)
        ax.text(i + 0.34, med, "mediana " + fmt.format(med),
                va="center", fontsize=8, color=TINTA_2)
        n = len(sub)
        desloc = rng.uniform(-0.14, 0.14, n)
        for (_, r), dx in zip(sub.iterrows(), desloc):
            ax.scatter(i + dx, r[col],
                       marker=MARCADOR.get(r["pessoa"], "o"),
                       s=52, facecolor=COR[t], edgecolor=TINTA,
                       linewidth=0.8, zorder=3)
    ax.set_xticks(range(len(ORDEM)))
    ax.set_xticklabels([ROTULO[t] for t in ORDEM], fontsize=10)
    ax.set_xlim(-0.6, 1.9)
    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    if log:
        ax.set_yscale("log")
        ticks = [t for t in [5, 10, 30, 60, 120, 300, 600]
                 if ylim is None or ylim[0] <= t <= ylim[1]]
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks])
        ax.minorticks_off()
    if ylim:
        ax.set_ylim(*ylim)


def _painel_pareado(ax, df, col, titulo, xlabel, xlim=None, log=False, fmt="{:.0f}"):
    """Grafico pareado por participante (mediana com_ia vs sem_ia)."""
    pessoas = sorted(df["pessoa"].unique())
    med = (df.dropna(subset=[col])
           .groupby(["pessoa", "tratamento"])[col]
           .median()
           .unstack("tratamento"))
    for y, p in enumerate(pessoas):
        v = med.loc[p]
        ax.hlines(y, v.min(), v.max(), color=EIXO, lw=3, zorder=1)
        for t in ORDEM:
            ax.scatter(v[t], y, s=70, color=COR[t],
                       marker=MARCADOR[p], zorder=3,
                       edgecolor=SUPERFICIE, linewidth=1.2)
            ax.annotate(fmt.format(v[t]), (v[t], y),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8, color=TINTA_2)
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


def gerar_graficos(df: pd.DataFrame,
                   pares_rq1: pd.DataFrame,
                   pares_rq2: pd.DataFrame):
    print(f"\n{SEP}")
    print("  GRAFICOS")
    print(SEP)

    # ── Prepara coluna taxa_sucesso em % (0-100) para os graficos ────────────
    df = df.copy()
    df["taxa_pct"] = df["taxa_sucesso"] * 100
    pares_rq2_pct = pares_rq2.copy()
    for c in ["com_ia", "sem_ia", "delta"]:
        pares_rq2_pct[c] = pares_rq2_pct[c] * 100

    # ── 1. RQ1 – Tempo ───────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    _painel_distribuicao(
        axes[0], df, "tempo_segundos",
        "Distribuicao por tratamento",
        "segundos (escala log)",
        log=True, ylim=(2, 700), fmt="{:.0f}s",
    )
    _painel_pareado(
        axes[1], df, "tempo_segundos",
        "Pareado por participante",
        "segundos (escala log)",
        log=True, xlim=(2.5, 500), fmt="{:.0f}s",
    )
    fig.suptitle("RQ1 - Tempo de resolucao (com IA vs sem IA)",
                 x=0.03, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.03, 0.915,
             "barra = IQR; traco = mediana; n = 6 trials por tratamento; "
             "direita: mediana dos 2 trials de cada participante",
             fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    _legenda(fig)
    _salvar(fig, "rq1_tempo.png")

    # ── 2. RQ2 – Taxa de sucesso ─────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    _painel_distribuicao(
        axes[0], df, "taxa_pct",
        "Distribuicao por tratamento",
        "% de testes passando",
        ylim=(0, 108), fmt="{:.0f}%",
    )
    axes[0].set_yticks([0, 25, 50, 75, 100])
    _painel_pareado(
        axes[1], df, "taxa_pct",
        "Pareado por participante",
        "% de testes passando",
        xlim=(60, 108), fmt="{:.0f}%",
    )
    fig.suptitle("RQ2 - Taxa de sucesso nos testes (com IA vs sem IA)",
                 x=0.03, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.03, 0.915,
             "barra = IQR; traco = mediana; n = 6 trials por tratamento; "
             "direita: mediana dos 2 trials de cada participante",
             fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.9))
    _legenda(fig)
    _salvar(fig, "rq2_taxa_sucesso.png")

    # ── 3. Combinado RQ1 + RQ2 ───────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    _painel_distribuicao(
        axes[0, 0], df, "tempo_segundos",
        "RQ1 - Tempo por tratamento",
        "segundos (escala log)",
        log=True, ylim=(2, 700), fmt="{:.0f}s",
    )
    _painel_pareado(
        axes[0, 1], df, "tempo_segundos",
        "RQ1 - Tempo pareado por participante",
        "segundos (escala log)",
        log=True, xlim=(2.5, 500), fmt="{:.0f}s",
    )
    _painel_distribuicao(
        axes[1, 0], df, "taxa_pct",
        "RQ2 - Taxa de sucesso por tratamento",
        "% de testes passando",
        ylim=(0, 108), fmt="{:.0f}%",
    )
    axes[1, 0].set_yticks([0, 25, 50, 75, 100])
    _painel_pareado(
        axes[1, 1], df, "taxa_pct",
        "RQ2 - Taxa de sucesso pareada por participante",
        "% de testes passando",
        xlim=(60, 108), fmt="{:.0f}%",
    )

    fig.suptitle("RQ1 e RQ2 - Tempo e Taxa de Sucesso (com IA vs sem IA)",
                 x=0.03, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.03, 0.963,
             "barra = IQR; traco = mediana; n = 6 trials por tratamento; "
             "paineis da direita: mediana dos 2 trials de cada participante (n = 3 pares)",
             fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    _legenda(fig)
    _salvar(fig, "rq1_rq2_combinado.png")


if __name__ == "__main__":
    main()

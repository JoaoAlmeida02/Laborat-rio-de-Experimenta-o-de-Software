"""Análise fatorial do desempenho, por endpoint e métrica."""
import argparse
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multitest import multipletests

PILOTO = "DADOS DO PILOTO: sem poder estatístico; não use para conclusões"
LEGADO = "status desconhecido; linhas tratadas como ok"
K_PROVISORIO = "O k é provisório: a análise de poder usa variabilidade assumida."
METRICAS = {
    "rps": "req/s", "p50_ms": "ms", "p95_ms": "ms", "p99_ms": "ms",
    "mem_php_media_mb": "MB", "mem_php_pico_mb": "MB", "taxa_erro": "proporção",
}
TRATAMENTOS = {
    "T1": ("8.4.26", 0), "T2": ("8.4.26", 1),
    "T3": ("8.4.27", 0), "T4": ("8.4.27", 1),
}
FORMULA = "y ~ C(php_version, Sum) * C(mitigacao, Sum)"
TERMOS = dict(zip(
    ("C(php_version, Sum)", "C(mitigacao, Sum)", "C(php_version, Sum):C(mitigacao, Sum)"),
    ("versao", "mitigacao", "interacao"),
))
CONTRASTES = {
    "T1 vs T3": ([-1, 0, 1, 0], ["T1"]),
    "versao": ([-.5, -.5, .5, .5], ["T1", "T2"]),
    "T1 vs T2": ([-1, 1, 0, 0], ["T1"]),
    "mitigacao": ([-.5, .5, -.5, .5], ["T1", "T3"]),
}


def detectar_entrada(dados=Path("dados")):
    bruto = dados / "brutos" / "dados.csv"
    return bruto if bruto.is_file() else dados / "piloto" / "piloto.csv"


def assinatura(entrada):
    """Identifica a versão dos dados mesmo após mover o projeto entre máquinas."""
    return sha256(Path(entrada).read_bytes()).hexdigest()


def carregar(entrada):
    return preparar(pd.read_csv(entrada, dtype={"php_version": str}))


def preparar(df):
    obrigatorias = {"execucao_id", "tratamento", "php_version", "mitigacao",
                    "repeticao", "endpoint", *METRICAS}
    faltam = obrigatorias.difference(df.columns)
    if faltam:
        raise ValueError(f"Colunas faltando: {', '.join(sorted(faltam))}")
    legado = "status" not in df
    status = (df.status.fillna("ausente").astype(str).str.strip().str.lower()
              if not legado else pd.Series("ok", index=df.index))
    validos = df.loc[status.eq("ok")].copy()
    for metrica in METRICAS:
        validos[metrica] = pd.to_numeric(validos[metrica], errors="coerce")
    incompletos = ~np.isfinite(validos[list(METRICAS)]).all(axis=1)
    info = {"legado": legado, "status_descartados": status[status.ne("ok")].value_counts().to_dict(),
            "linhas_incompletas": int(incompletos.sum()),
            "execucoes_descartadas": len(set(df.execucao_id) - set(validos.loc[~incompletos, "execucao_id"]))}
    validos = validos.loc[~incompletos].copy()
    if validos.empty:
        raise ValueError("Sem execuções válidas após verificar status e métricas.")
    for tratamento, (php, mitigacao) in TRATAMENTOS.items():
        linhas = validos.tratamento.eq(tratamento)
        if not (validos.loc[linhas, "php_version"].eq(php)
                & validos.loc[linhas, "mitigacao"].astype(str).eq(str(mitigacao))).all():
            raise ValueError(f"Versão ou estado da mitigação incompatível com {tratamento}.")
    if not validos.tratamento.isin(TRATAMENTOS).all():
        raise ValueError("Tratamento desconhecido.")
    if validos[["execucao_id", "endpoint"]].isna().any().any() or validos.duplicated(
        ["execucao_id", "endpoint"]
    ).any():
        raise ValueError("Execução/endpoint ausente ou duplicado.")
    if (validos[list(METRICAS)] < 0).any().any() or (validos.taxa_erro > 1).any():
        raise ValueError("Métricas negativas ou taxa de erro fora do intervalo [0, 1].")
    return validos, info


def avisos_amostra(df, entrada, sintetico=False):
    contagens = df.groupby(["endpoint", "tratamento"]).execucao_id.nunique().unstack()
    contagens = contagens.reindex(columns=list(TRATAMENTOS)).fillna(0)
    avisos = ["SINTÉTICO"] if sintetico else []
    if "piloto" in Path(entrada).parts or (contagens < 5).any().any():
        avisos.append(PILOTO)
    return avisos


def ajustar_holm(tabela, bruto="p"):
    tabela["p_holm"] = np.nan
    validos = tabela[bruto].notna()
    if validos.any():
        tabela.loc[validos, "p_holm"] = multipletests(tabela.loc[validos, bruto], method="holm")[1]
    return tabela


def efeitos(dados, metrica, alfa):
    trabalho = dados[["php_version", "mitigacao", "tratamento"]].copy()
    y = dados[metrica]
    log = metrica in ("rps", "p50_ms", "p95_ms", "p99_ms") and y.gt(0).all()
    trabalho["y"] = np.log(y) if log else y
    escala = "log natural" if log else ("proporção" if metrica == "taxa_erro" else "original")
    grupos = [trabalho.loc[trabalho.tratamento.eq(t), "y"] for t in TRATAMENTOS]
    linhas = {nome: dict(efeito=nome, escala=escala, teste="indisponível",
                         motivo="Cada célula precisa de pelo menos duas observações.",
                         p_shapiro=np.nan, p_levene=np.nan, p=np.nan, f=np.nan,
                         eta2_parcial=np.nan, magnitude="indisponível") for nome in TERMOS.values()}
    if min(map(len, grupos)) < 2:
        return list(linhas.values())

    modelo = ols(FORMULA, trabalho).fit()
    residuos = modelo.resid
    shapiro = stats.shapiro(residuos).pvalue if np.ptp(residuos) > 1e-12 else np.nan
    desvios = np.concatenate([g - g.median() for g in grupos])
    levene = stats.levene(*grupos, center="median").pvalue if np.ptp(abs(desvios)) > 1e-12 else np.nan
    parametrico = shapiro >= alfa and levene >= alfa
    y = trabalho.y
    celula = trabalho.groupby("tratamento").y.transform("mean")
    # Médias marginais com pesos iguais por célula, inclusive em desenho desbalanceado.
    medias = trabalho.groupby(["php_version", "mitigacao"]).y.mean()
    versao = trabalho.php_version.map(medias.groupby(level=0).mean())
    mitigacao = trabalho.mitigacao.map(medias.groupby(level=1).mean())
    media = medias.mean()
    alinhados = {
        "versao": y - celula + versao,
        "mitigacao": y - celula + mitigacao,
        "interacao": y - versao - mitigacao + media,
    }
    tabela_anova = anova_lm(modelo, typ=2) if parametrico else None
    for termo, nome in TERMOS.items():
        linha = linhas[nome]
        linha.update(p_shapiro=shapiro, p_levene=levene)
        if np.ptp(residuos) <= 1e-12:
            linha["motivo"] = "Resíduos sem variabilidade estimável."
            continue
        if parametrico:
            tabela = tabela_anova
            linha.update(teste="ANOVA tipo II", motivo="Shapiro–Wilk e Levene não rejeitaram os pressupostos.")
        else:
            # ART: isola cada efeito, ranqueia (empates pela média) e testa só o termo alinhado.
            ranks = stats.rankdata(np.round(alinhados[nome], 12))
            tabela = anova_lm(ols(FORMULA, trabalho.assign(y=ranks)).fit(), typ=2)
            linha.update(teste="ART-ANOVA tipo II",
                         motivo="Shapiro–Wilk ou Levene rejeitou ou foi indeterminado.")
        ss = tabela.loc[termo, "sum_sq"]
        total = ss + tabela.loc["Residual", "sum_sq"]
        eta = ss / total if total > 0 else np.nan
        magnitude = ("grande" if eta >= .14 else "médio" if eta >= .06
                     else "pequeno" if eta >= .01 else "desprezível")
        linha.update(p=tabela.loc[termo, "PR(>F)"], f=tabela.loc[termo, "F"],
                     eta2_parcial=eta, magnitude=magnitude)
    return list(linhas.values())


def tost(dados, metrica, margem, alfa):
    grupos = {t: dados.loc[dados.tratamento.eq(t), metrica] for t in TRATAMENTOS}
    for nome, (pesos, referencias) in CONTRASTES.items():
        referencia = pd.concat([grupos[t] for t in referencias]).median()
        limite = margem * abs(referencia)
        linha = dict(contraste=nome, referencia=referencia, margem=limite,
                     margem_relativa=margem, diferenca=np.nan, ic90_inferior=np.nan,
                     ic90_superior=np.nan, p=np.nan, p_fora=np.nan,
                     motivo="Células insuficientes ou variância indeterminada.")
        ativos = [(w, g) for w, g in zip(pesos, grupos.values()) if w]
        if min(len(g) for _, g in ativos) >= 2:
            # Contrastes de médias com erro padrão de Welch–Satterthwaite.
            delta = sum(w * g.mean() for w, g in ativos)
            variancias = np.array([w**2 * g.var() / len(g) for w, g in ativos])
            erro = np.sqrt(variancias.sum())
            linha["diferenca"] = delta
            if erro > 0:
                gl = variancias.sum()**2 / sum(v**2 / (len(g)-1) for v, (_, g) in zip(variancias, ativos))
                semi = stats.t.ppf(.95, gl) * erro
                linha.update(ic90_inferior=delta-semi, ic90_superior=delta+semi)
                if limite > 0:
                    inferior = stats.t.sf((delta + limite) / erro, gl)
                    superior = stats.t.cdf((delta - limite) / erro, gl)
                    fora = min(1, 2 * min(stats.t.sf((delta-limite)/erro, gl),
                                          stats.t.cdf((delta+limite)/erro, gl)))
                    linha.update(p=max(inferior, superior), p_fora=fora, motivo="Welch–Satterthwaite.")
                elif limite == 0:
                    linha["motivo"] = "Mediana de referência zero: margem relativa nula."
        yield linha


def analisar(df, alfa=.05, margem=.05):
    descritiva, anova, equivalencia = [], [], []
    for endpoint, dados in df.groupby("endpoint"):
        for metrica in METRICAS:
            chave = dict(endpoint=endpoint, metrica=metrica)
            for tratamento in TRATAMENTOS:
                valores = dados.loc[dados.tratamento.eq(tratamento), metrica]
                descritiva.append(dict(**chave, tratamento=tratamento, n=len(valores),
                                       mediana=valores.median(), media=valores.mean(),
                                       iqr=valores.quantile(.75)-valores.quantile(.25), desvio=valores.std()))
            anova.extend(dict(**chave, **linha) for linha in efeitos(dados, metrica, alfa))
            equivalencia.extend(dict(**chave, **linha) for linha in tost(dados, metrica, margem, alfa))
    a = ajustar_holm(pd.DataFrame(anova))
    e = ajustar_holm(pd.DataFrame(equivalencia))
    e["p_fora_holm"] = ajustar_holm(e[["p_fora"]].copy(), "p_fora").p_holm
    e["conclusao"] = np.select([e.p_holm.lt(alfa), e.p_fora_holm.lt(alfa)],
                               ["equivalente", "não equivalente"], default="inconclusivo")
    return pd.DataFrame(descritiva), a, e


def aviso_k(saida):
    caminho = Path(saida) / "poder_k.csv"
    if caminho.is_file() and pd.read_csv(caminho).get("origem", pd.Series(dtype=str)).eq("assumido").any():
        return [K_PROVISORIO]
    return []


def resumo(d, a, e, info, avisos, alfa):
    linhas = ["# RQ1 e RQ2 — Desempenho", "", *[f"> {aviso}\n" for aviso in avisos]]
    if info["legado"]:
        linhas.append(f"> {LEGADO}\n")
    linhas += [f"Execuções inteiramente descartadas: {info['execucoes_descartadas']}. "
               f"Linhas descartadas por status: {info['status_descartados'] or 'nenhuma'}. "
               f"Linhas com métricas ausentes ou inválidas: {info['linhas_incompletas']}.",
               "", "A análise mantém os outliers. RPS e latências usam log natural quando "
               "estritamente positivos na ANOVA. Taxa de erro é uma proporção por execução. "
               "Quando os pressupostos falham, o ART alinha separadamente cada efeito antes do ranqueamento.",
               "", "O TOST usa diferenças de médias na escala original. A margem vem da mediana "
               "de referência. Os ICs de 90% são nominais. Holm é aplicado separadamente às famílias "
               "ANOVA, TOST e testes de diferença além da margem.", ""]
    for rq, efeito, contrastes in [("RQ1 — Correção", "versao", ["T1 vs T3", "versao"]),
                                   ("RQ2 — Mitigação", "mitigacao", ["T1 vs T2", "mitigacao"])]:
        foco = a[a.efeito.eq(efeito)]
        linhas += [f"## {rq}", "",
                   f"Entre {foco.p_holm.notna().sum()} testes estimáveis, "
                   f"{foco.p_holm.lt(alfa).sum()} detectaram efeito após Holm (α = {alfa:g})."]
        for item in e[e.contraste.isin(contrastes)].itertuples():
            p = f"{item.p_holm:.3g}" if pd.notna(item.p_holm) else "indisponível"
            delta = f"{item.diferenca:.4g} {METRICAS[item.metrica]}" if pd.notna(item.diferenca) else "indisponível"
            linhas.append(f"- {item.endpoint} / {item.metrica} ({item.contraste}): Δ {delta}, "
                          f"p TOST ajustado {p}, {item.conclusao}.")
        linhas.append("")
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=detectar_entrada())
    parser.add_argument("--saida", type=Path, default=Path("resultados"))
    parser.add_argument("--alfa", type=float, default=.05)
    parser.add_argument("--margem", type=float, default=.05)
    args = parser.parse_args()
    if not 0 < args.alfa < .5 or not 0 < args.margem < 1:
        parser.error("--alfa deve estar entre 0 e 0,5 e --margem entre 0 e 1.")
    try:
        df, info = carregar(args.entrada)
    except (OSError, ValueError) as erro:
        parser.error(str(erro))
    d, a, e = analisar(df, args.alfa, args.margem)
    avisos = avisos_amostra(df, args.entrada) + aviso_k(args.saida)
    origem = assinatura(args.entrada)
    args.saida.mkdir(parents=True, exist_ok=True)
    for nome, tabela in [("descritiva", d), ("anova", a), ("tost", e)]:
        tabela["origem"] = origem
        tabela["alfa"] = args.alfa
        tabela["avisos"] = " | ".join(avisos)
        tabela.to_csv(args.saida / f"rq1_rq2_{nome}.csv", index=False)
    (args.saida / "rq1_rq2_resumo.md").write_text(resumo(d, a, e, info, avisos, args.alfa), encoding="utf-8")


if __name__ == "__main__":
    main()


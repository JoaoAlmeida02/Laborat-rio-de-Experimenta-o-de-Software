"""Tempo até a primeira correção, com censura à direita."""
import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test
from lifelines.utils import median_survival_times

if __package__:
    from .analise_rq1_rq2 import ajustar_holm, aviso_k, avisos_amostra, carregar, detectar_entrada
else:
    from analise_rq1_rq2 import ajustar_holm, aviso_k, avisos_amostra, carregar, detectar_entrada

GRUPOS = {"comunitario": "Distribuição Linux", "comercial": "Distribuição Linux",
          "nuvem": "Nuvem", "hospedagem": "Hospedagem"}
BAIXO_PODER = ("Poucos eventos por grupo. Log-rank de baixo poder e não conclusivo. "
               "A amostra pequena é uma ameaça à validade de conclusão.")
PRINCIPAL = "Principal"
EXPLORATORIA = "Exploratória — Linux"


def carregar_rq3(entrada):
    df = pd.read_csv(entrada)
    faltam = {"distribuidor", "grupo", "tempo_dias", "evento", "incluir_analise"} - set(df)
    if faltam:
        raise ValueError(f"Colunas faltando na RQ3: {', '.join(sorted(faltam))}")
    df["tipo"] = df.grupo.map(GRUPOS)
    aptos = df.loc[df.incluir_analise.eq("sim")].copy()
    if aptos.empty:
        raise ValueError("Sem distribuidores elegíveis para a RQ3.")
    aptos["tempo_dias"] = pd.to_numeric(aptos.tempo_dias, errors="coerce")
    aptos["evento"] = pd.to_numeric(aptos.evento, errors="coerce")
    if (aptos.tipo.isna().any() or not np.isfinite(aptos.tempo_dias).all()
            or aptos.tempo_dias.lt(0).any() or not aptos.evento.isin([0, 1]).all()):
        raise ValueError("RQ3 contém grupo, tempo ou evento inválido em uma linha elegível.")
    aptos["evento"] = aptos.evento.astype(int)
    return df, aptos


def pouco_poder(df, coluna):
    eventos = df.groupby(coluna).evento.sum()
    return len(eventos) < 2 or eventos.lt(5).any()


def analises(df):
    linux = df[df.tipo.eq("Distribuição Linux")]
    return [(PRINCIPAL, df, "tipo"), (EXPLORATORIA, linux, "grupo")]


def km_grupo(df):
    km = KaplanMeierFitter().fit(df.tempo_dias, event_observed=df.evento, label="sem_correcao")
    ic = km.confidence_interval_
    limites = median_survival_times(ic).iloc[0]
    n = len(df)
    eventos = int(df.evento.sum())
    mediana = [km.median_survival_time_, limites.iloc[0], limites.iloc[1]]
    mediana = [float(v) if np.isfinite(v) else np.nan for v in mediana]
    estatisticas = dict(n=n, eventos=eventos, censurados=n-eventos, mediana_dias=mediana[0],
                        ic95_mediana_inferior=mediana[1], ic95_mediana_superior=mediana[2])
    curva = pd.concat([km.survival_function_, ic, km.event_table[["at_risk", "censored"]]], axis=1)
    curva.columns = ["sem_correcao", "ic95_inferior", "ic95_superior", "em_risco", "censuras_no_dia"]
    return estatisticas, curva.rename_axis("tempo_dias").reset_index()


def analisar_rq3(df):
    curvas, testes = [], []
    for escopo, amostra, coluna in analises(df):
        grupos = list(amostra.groupby(coluna))
        if not grupos:
            continue
        baixo = pouco_poder(amostra, coluna)
        for grupo, dados in [("Geral", amostra), *grupos]:
            numeros, curva = km_grupo(dados)
            curvas.append(curva.assign(analise=escopo, grupo=grupo, baixo_poder=baixo, **numeros))
        linhas = []
        if len(grupos) > 2:
            teste = multivariate_logrank_test(amostra.tempo_dias, amostra[coluna], amostra.evento)
            linhas.append(dict(comparacao="Multigrupo", grupo_a="", grupo_b="",
                               estatistica=teste.test_statistic, p=teste.p_value))
        for (a, g1), (b, g2) in combinations(grupos, 2):
            teste = logrank_test(g1.tempo_dias, g2.tempo_dias, g1.evento, g2.evento)
            linhas.append(dict(comparacao="Par a par", grupo_a=a, grupo_b=b,
                               estatistica=teste.test_statistic, p=teste.p_value))
        if linhas:
            tabela = pd.DataFrame(linhas)
            pares = tabela.comparacao.eq("Par a par")
            tabela["p_holm"] = tabela.p
            tabela.loc[pares, "p_holm"] = ajustar_holm(tabela.loc[pares].copy()).p_holm
            testes.append(tabela.assign(analise=escopo, baixo_poder=baixo,
                                        interpretacao="Não conclusivo — baixo poder" if baixo else "Consultar p ajustado"))
    colunas = ["analise", "comparacao", "grupo_a", "grupo_b", "estatistica", "p", "p_holm",
               "baixo_poder", "interpretacao"]
    logrank = pd.concat(testes, ignore_index=True)[colunas] if testes else pd.DataFrame(columns=colunas)
    return pd.concat(curvas, ignore_index=True), logrank


def resumo_rq3(df, km, logrank, avisos):
    linhas = ["# RQ3 — Tempo até a primeira correção", "", *[f"> {a}\n" for a in avisos],
              f"Origem temporal: 21/10/2026. Registros fora da análise: {len(df)-int(df.incluir_analise.eq('sim').sum())}.",
              "IC de 95% da mediana obtido pela inversão das bandas Kaplan–Meier.", ""]
    formatar = lambda v: f"{v:g}" if pd.notna(v) else "não estimável"
    for (escopo, grupo), sub in km.groupby(["analise", "grupo"], sort=False):
        r = sub.iloc[0]
        linhas.append(f"- {escopo} / {grupo}: n={r.n}, {r.eventos} eventos, {r.censurados} censurados. "
                      f"Mediana em dias: {formatar(r.mediana_dias)} "
                      f"(IC 95% {formatar(r.ic95_mediana_inferior)} a {formatar(r.ic95_mediana_superior)}).")
    linhas += ["", "Holm é aplicado às comparações par a par de cada análise.", ""]
    for r in logrank.itertuples():
        nome = f"{r.grupo_a} × {r.grupo_b}" if r.grupo_a else r.comparacao
        linhas.append(f"- {r.analise} / {nome}: p bruto {formatar(r.p)}, p ajustado {formatar(r.p_holm)}.")
    if logrank.empty:
        linhas.append("Log-rank indisponível: são necessários pelo menos dois grupos.")
    return "\n".join(linhas) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("dados/rq3_correcoes.csv"))
    parser.add_argument("--entrada-desempenho", type=Path, default=detectar_entrada(),
                        help="Entrada opcional para propagar o aviso de piloto ao resumo.")
    parser.add_argument("--saida", type=Path, default=Path("resultados"))
    args = parser.parse_args()
    try:
        todos, aptos = carregar_rq3(args.entrada)
    except (OSError, ValueError) as erro:
        parser.error(str(erro))
    km, logrank = analisar_rq3(aptos)
    avisos = aviso_k(args.saida)
    if args.entrada_desempenho.is_file():
        try:
            desempenho, _ = carregar(args.entrada_desempenho)
            avisos += avisos_amostra(desempenho, args.entrada_desempenho)
        except (OSError, ValueError) as erro:
            print(f"Aviso: não foi possível verificar a amostra de desempenho: {erro}")
    if km.baixo_poder.any():
        avisos.append(BAIXO_PODER)
    args.saida.mkdir(parents=True, exist_ok=True)
    km.to_csv(args.saida / "rq3_km_tabela.csv", index=False)
    logrank.to_csv(args.saida / "rq3_logrank.csv", index=False)
    (args.saida / "rq3_resumo.md").write_text(resumo_rq3(todos, km, logrank, avisos), encoding="utf-8")


if __name__ == "__main__":
    main()


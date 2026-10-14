import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

RAIZ = Path(__file__).resolve().parents[1]
DIMENSOES = ["tipo_projeto", "entrega_real", "corretiva"]


def interpretar_landis_koch(kappa: float) -> str:
    if kappa < 0.0:
        return "Pobre (Poor)"
    elif kappa <= 0.20:
        return "Leve (Slight)"
    elif kappa <= 0.40:
        return "Razoável (Fair)"
    elif kappa <= 0.60:
        return "Moderada (Moderate)"
    elif kappa <= 0.80:
        return "Substancial (Substantial)"
    else:
        return "Quase Perfeita (Almost Perfect)"


def carregar_planilhas(
    pasta: Path | str, sufixos: Tuple[str, ...] = ("A", "B", "C")
) -> Dict[str, pd.DataFrame]:
    pasta = Path(pasta)
    planilhas = {}
    for s in sufixos:
        arq = pasta / f"rotulos_{s}.csv"
        if not arq.exists():
            raise FileNotFoundError(f"Planilha de rotulagem não encontrada: {arq}")
        df = pd.read_csv(arq, dtype=str).fillna("")
        planilhas[s] = df
    return planilhas


def calcular_fleiss_kappa_dimensao(
    planilhas: Dict[str, pd.DataFrame], dimensao: str
) -> Tuple[float, str]:
    avaliadores = sorted(planilhas.keys())
    n_itens = len(planilhas[avaliadores[0]])

    matriz = []
    for i in range(n_itens):
        linha = [planilhas[av].iloc[i][dimensao].strip() for av in avaliadores]
        matriz.append(linha)

    tabela, categorias = aggregate_raters(matriz)
    if tabela.shape[1] <= 1:
        kappa = 1.0
    else:
        kappa = float(fleiss_kappa(tabela))

    interpretacao = interpretar_landis_koch(kappa)
    return kappa, interpretacao


CATEGORIAS_POR_DIMENSAO = {
    "tipo_projeto": [
        "biblioteca_framework",
        "aplicacao_servico",
        "ferramenta_cli",
        "outro",
    ],
    "entrega_real": ["sim", "nao", "incerto"],
    "corretiva": ["sim", "nao"],
}


def calcular_cohen_kappa_pares(
    planilhas: Dict[str, pd.DataFrame], dimensao: str
) -> Dict[str, float]:
    pares = [("A", "B"), ("A", "C"), ("B", "C")]
    resultados = {}
    rotulos_validos = CATEGORIAS_POR_DIMENSAO.get(dimensao)

    for p1, p2 in pares:
        if p1 in planilhas and p2 in planilhas:
            v1 = planilhas[p1][dimensao].str.strip().tolist()
            v2 = planilhas[p2][dimensao].str.strip().tolist()
            if v1 == v2:
                resultados[f"{p1}x{p2}"] = 1.0
                continue
            try:
                val = float(cohen_kappa_score(v1, v2, labels=rotulos_validos))
                if pd.isna(val):
                    val = 1.0 if v1 == v2 else 0.0
            except Exception:
                val = 1.0 if v1 == v2 else 0.0
            resultados[f"{p1}x{p2}"] = round(val, 4)
    return resultados


def extrair_divergencias(
    planilhas: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    df_a = planilhas["A"]
    df_b = planilhas["B"]
    df_c = planilhas["C"]
    divergencias = []

    for i in range(len(df_a)):
        repo = df_a.iloc[i].get("repo", "")
        tag = df_a.iloc[i].get("release_tag", "")
        rel_url = df_a.iloc[i].get("release_url", "")
        cmp_url = df_a.iloc[i].get("compare_url", "")

        for dim in DIMENSOES:
            val_a = df_a.iloc[i][dim].strip()
            val_b = df_b.iloc[i][dim].strip()
            val_c = df_c.iloc[i][dim].strip()

            if not (val_a == val_b == val_c):
                divergencias.append(
                    {
                        "indice": i + 1,
                        "repo": repo,
                        "release_tag": tag,
                        "release_url": rel_url,
                        "compare_url": cmp_url,
                        "dimensao": dim,
                        "rotulo_A": val_a,
                        "rotulo_B": val_b,
                        "rotulo_C": val_c,
                        "tipo_divergencia": "1-1-1 (empate)"
                        if (val_a != val_b and val_a != val_c and val_b != val_c)
                        else "2-1 (maioria)",
                    }
                )

    return divergencias


def gerar_relatorio_divergencias_md(
    divergencias: List[Dict[str, Any]], caminho_saida: Path | str
) -> None:
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    linhas_md = [
        "# Relatório de Divergências de Rotulagem (Pauta de Consenso)",
        "",
        "Este relatório lista todos os casos onde houve discordância entre os avaliadores (A, B e C) ",
        "durante a validação da amostra-ouro. Serve como **pauta oficial da reunião de consenso**.",
        "",
        f"**Total de divergências registradas:** {len(divergencias)}",
        "",
        "| # | Repositório | Release | Dimensão | Avaliador A | Avaliador B | Avaliador C | Padrão | Links |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for d in divergencias:
        link_rel = f"[Release]({d['release_url']})" if d["release_url"] and d["release_url"] != "-" else "-"
        link_cmp = f"[Compare]({d['compare_url']})" if d["compare_url"] and d["compare_url"] != "-" else "-"
        links_juntos = f"{link_rel} · {link_cmp}"

        linhas_md.append(
            f"| {d['indice']} | `{d['repo']}` | `{d['release_tag']}` | **{d['dimensao']}** | "
            f"`{d['rotulo_A']}` | `{d['rotulo_B']}` | `{d['rotulo_C']}` | {d['tipo_divergencia']} | {links_juntos} |"
        )

    linhas_md.append("")
    caminho_saida.write_text("\n".join(linhas_md), encoding="utf-8")


def avaliar_concordancia_completa(
    pasta_rotulagem: Path | str,
) -> Dict[str, Any]:
    pasta = Path(pasta_rotulagem)
    planilhas = carregar_planilhas(pasta)

    resultado = {
        "fleiss": {},
        "cohen": {},
        "divergencias_total": 0,
    }

    for dim in DIMENSOES:
        kappa, interp = calcular_fleiss_kappa_dimensao(planilhas, dim)
        resultado["fleiss"][dim] = {
            "kappa": round(kappa, 4),
            "interpretacao": interp,
        }
        pares = calcular_cohen_kappa_pares(planilhas, dim)
        resultado["cohen"][dim] = pares

    divergencias = extrair_divergencias(planilhas)
    resultado["divergencias_total"] = len(divergencias)
    gerar_relatorio_divergencias_md(divergencias, pasta / "divergencias.md")

    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pasta",
        default=str(RAIZ / "rotulagem"),
        help="Diretório contendo rotulos_A.csv, rotulos_B.csv, rotulos_C.csv",
    )
    args = parser.parse_args(argv)

    pasta = Path(args.pasta)
    print("=" * 65)
    print(" ANÁLISE DE CONCORDÂNCIA INTEROBSERVADORES - SPRINT 2 (LAB03S02) ")
    print("=" * 65)

    resultados = avaliar_concordancia_completa(pasta)

    print("\n--- 1. KAPPA DE FLEISS GLOBAL (Landis & Koch, 1977) ---")
    for dim, info in resultados["fleiss"].items():
        print(f" • {dim:<18}: {info['kappa']:>6.4f} -> {info['interpretacao']}")

    print("\n--- 2. KAPPA DE COHEN PAR A PAR (Inovação: A×B, A×C, B×C) ---")
    for dim, pares in resultados["cohen"].items():
        pares_str = " | ".join(f"{par}: {v:>6.4f}" for par, v in pares.items())
        print(f" • {dim:<18}: {pares_str}")

    print("\n--- 3. RELATÓRIO DE DIVERGÊNCIAS ---")
    print(f" Total de divergências encontradas: {resultados['divergencias_total']}")
    print(f" Relatório detalhado salvo em: {pasta / 'divergencias.md'}")
    print("=" * 65)


if __name__ == "__main__":
    main()

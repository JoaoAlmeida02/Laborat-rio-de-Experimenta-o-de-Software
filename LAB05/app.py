"""Dashboard interativo do LAB05. Execute streamlit run app.py."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"
RESULTADOS = RAIZ / "resultados"

TRATAMENTOS = pd.DataFrame(
    {
        "Tratamento": ["T1", "T2", "T3", "T4"],
        "PHP": ["8.4.26 (vulnerável)", "8.4.26 (vulnerável)", "8.4.27 (corrigido)", "8.4.27 (corrigido)"],
        "Mitigação": ["Desligada", "Ligada", "Desligada", "Ligada"],
        "session.upload_progress.enabled": ["1 (padrão)", "0 (mitigação)", "1 (padrão)", "0 (mitigação)"],
    }
)



from scripts.analise_rq1_rq2 import (
    LEGADO, METRICAS, assinatura, aviso_k, avisos_amostra, detectar_entrada, preparar,
)
from scripts.analise_rq3 import BAIXO_PODER, EXPLORATORIA, GRUPOS, PRINCIPAL
from scripts.graficos import CORES


@st.cache_data
def ler_csv(caminho, versao=None):
    return pd.read_csv(caminho) if Path(caminho).is_file() else None


def carregar_csv(caminho):
    try:
        return ler_csv(caminho, caminho.stat().st_mtime_ns)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as erro:
        st.warning(f"Não foi possível ler {caminho.name}: {erro}")
        return None


def filtrar(df, filtros):
    if df is None:
        return None
    for coluna, selecao in filtros.items():
        if coluna in df:
            df = df[df[coluna].isin(selecao)]
    return df


def tabela(df, aviso):
    if df is None or df.empty:
        st.info(aviso)
    else:
        st.dataframe(df, hide_index=True, width="stretch")


def mostrar(fig, avisos, chave):
    fig.update_layout(colorway=list(CORES.values()))
    st.plotly_chart(fig, width="stretch", key=chave)
    for aviso in avisos:
        st.caption(aviso)


def rotulo(metrica):
    return f"{metrica} ({METRICAS[metrica]})"


def cartoes(df, metrica, contraste=("T1", "T3")):
    if df is None or df.empty:
        st.info("Sem execuções válidas para os filtros selecionados.")
        return
    colunas = st.columns(6)
    for col, nome, campo, formato in zip(colunas, ["RPS", "Latência p95", "Memória média", "Taxa de erro"],
                                        ["rps", "p95_ms", "mem_php_media_mb", "taxa_erro"],
                                        [".2f", ".2f", ".2f", ".2%"]):
        unidade = "" if campo == "taxa_erro" else f" {METRICAS[campo]}"
        col.metric(nome, f"{df[campo].median():{formato}}{unidade}")
    colunas[4].metric("Execuções", df.execucao_id.nunique())
    medianas = df.groupby("tratamento")[metrica].median()
    base, alvo = [medianas.get(t, np.nan) for t in contraste]
    delta = f"{(alvo-base)/base:+.2%}" if np.isfinite([base, alvo]).all() and base else "—"
    colunas[5].metric(f"Δ {contraste[1]} vs {contraste[0]} · {metrica}", delta)


def intervalos(df, metrica, avisos, chave):
    fig = go.Figure()
    for i, r in enumerate(df.itertuples()):
        nome = f"{r.endpoint} · {r.contraste}"
        if pd.notna(r.margem):
            fig.add_shape(type="rect", x0=-r.margem, x1=r.margem, y0=i-.3, y1=i+.3,
                          fillcolor=CORES["T3"], opacity=.18, line_width=0)
        if pd.notna(r.ic90_inferior):
            fig.add_trace(go.Scatter(x=[r.diferenca], y=[i], mode="markers", name=nome,
                                     error_x=dict(type="data", symmetric=False,
                                                  array=[r.ic90_superior-r.diferenca],
                                                  arrayminus=[r.diferenca-r.ic90_inferior])))
    fig.add_vline(x=0, line_dash="dot")
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(df))),
                     ticktext=[f"{r.endpoint} · {r.contraste}" for r in df.itertuples()])
    fig.update_layout(title="TOST · IC 90% e faixa de equivalência", xaxis_title=rotulo(metrica),
                      height=max(350, 130+34*len(df)))
    mostrar(fig, avisos, chave)


def painel_desempenho(df, metrica, avisos, estatisticas, rq):
    contraste = ("T1", "T3") if rq == 1 else ("T1", "T2")
    efeito = "versao" if rq == 1 else "mitigacao"
    cartoes(df, metrica, contraste)
    if df is not None and not df.empty:
        fig = px.box(df, x="tratamento", y=metrica, color="tratamento", facet_col="endpoint",
                     points="all", color_discrete_map=CORES, labels={metrica: rotulo(metrica)},
                     title="Distribuição por tratamento")
        mostrar(fig, avisos, f"box{rq}")
        rng = np.random.default_rng(502)
        linhas = []
        for (endpoint, tratamento), grupo in df.groupby(["endpoint", "tratamento"]):
            valores = grupo[metrica].to_numpy()
            limites = (np.quantile(np.median(rng.choice(valores, (2000, len(valores))), axis=1),
                                  [.025, .975]) if len(valores) > 1 else [np.nan, np.nan])
            mediana = np.median(valores)
            linhas.append(dict(endpoint=endpoint, tratamento=tratamento, mediana=mediana,
                               superior=max(0, limites[1]-mediana) if np.isfinite(limites[1]) else np.nan,
                               inferior=max(0, mediana-limites[0]) if np.isfinite(limites[0]) else np.nan))
        barras = pd.DataFrame(linhas)
        fig = px.bar(barras, x="tratamento", y="mediana", color="tratamento", facet_col="endpoint",
                     error_y="superior", error_y_minus="inferior", color_discrete_map=CORES,
                     labels={"mediana": rotulo(metrica)}, title="Medianas e IC 95% bootstrap")
        mostrar(fig, avisos, f"mediana{rq}")
        fator = "php_version" if rq == 1 else "Mitigação"
        medias = df.assign(Mitigação=df.mitigacao.map({0: "Desligada", 1: "Ligada"}))
        medias = medias.groupby(["endpoint", "php_version", "Mitigação"], as_index=False)[metrica].median()
        fig = px.line(medias.sort_values(fator), x=fator, y=metrica,
                      color="Mitigação" if rq == 1 else "php_version", facet_col="endpoint",
                      markers=True, title="Medianas por versão e estado da mitigação",
                      labels={metrica: rotulo(metrica), "php_version": "Versão do PHP"})
        mostrar(fig, avisos, f"interacao{rq}")
    d, a, e = estatisticas
    st.subheader("Descritiva")
    tabela(d, "Gere a descritiva com o script de RQ1/RQ2.")
    st.subheader("ANOVA e η² parcial")
    tabela(filtrar(a, {"efeito": [efeito, "interacao"]}), "ANOVA indisponível para a seleção.")
    st.subheader("Equivalência")
    e = filtrar(e, {"contraste": [f"T1 vs {contraste[1]}", efeito]})
    if e is not None and not e.empty:
        intervalos(e, metrica, avisos, f"tost{rq}")
    tabela(e, "TOST indisponível para a seleção.")


def filtrar_inferencia(a, e, tratamentos):
    # As tabelas preservam a família original de Holm e ocultam contrastes sem suas células.
    selecionados = set(tratamentos)
    contrastes = [nome for nome, exige in {"T1 vs T3": {"T1", "T3"}, "T1 vs T2": {"T1", "T2"},
                                           "versao": {"T1", "T2", "T3", "T4"},
                                           "mitigacao": {"T1", "T2", "T3", "T4"}}.items()
                  if exige <= selecionados]
    return (a if {"T1", "T2", "T3", "T4"} <= selecionados else filtrar(a, {"efeito": []}),
            filtrar(e, {"contraste": contrastes}))


def fonte_desempenho(tabela_resultado, origem):
    if tabela_resultado is None or "origem" not in tabela_resultado or origem is None:
        return None
    tabela_resultado = tabela_resultado[tabela_resultado.origem.eq(origem)]
    if tabela_resultado.empty:
        return None
    return tabela_resultado.drop(columns=["origem", "avisos"], errors="ignore")


def painel_rq3(raw, km, logrank, avisos):
    if raw is not None and {"evento", "incluir_analise"} <= set(raw):
        elegiveis = raw[raw.incluir_analise.eq("sim")]
        cols = st.columns(3)
        cols[0].metric("Distribuidores elegíveis", len(elegiveis))
        cols[1].metric("Correções observadas", int(elegiveis.evento.eq(1).sum()))
        cols[2].metric("Censurados", int(elegiveis.evento.eq(0).sum()))
        visivel = raw.assign(censurado=raw.evento.map({0: "Sim", 1: "Não"}).fillna("Fora da análise"))
        campos = ["distribuidor", "grupo", "tipo", "data_primeira_correcao", "tempo_dias", "censurado"]
        tabela(visivel[[c for c in campos if c in visivel]], "Sem distribuidores para a seleção.")
    else:
        st.warning("Dados da RQ3 indisponíveis em dados/rq3_correcoes.csv.")
    if km is None or km.empty:
        st.info("Gere as curvas, medianas e testes com scripts/analise_rq3.py.")
        return
    for escopo, dados in km.groupby("analise", sort=False):
        st.subheader(escopo)
        fig = go.Figure()
        for grupo, curva in dados[dados.grupo.ne("Geral")].groupby("grupo"):
            cor = CORES[grupo]
            x = [0, *curva.tempo_dias]
            fig.add_scatter(x=x, y=[1, *curva.ic95_superior], line=dict(width=0, shape="hv"),
                            legendgroup=grupo, showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=x, y=[1, *curva.ic95_inferior], line=dict(width=0, shape="hv"),
                            fill="tonexty", fillcolor=f"rgba({','.join(str(int(cor[i:i+2],16)) for i in (1,3,5))},0.16)",
                            legendgroup=grupo, showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=x, y=[1, *curva.sem_correcao], name=grupo, legendgroup=grupo,
                            line=dict(color=cor, shape="hv"))
            censura = curva[curva.censuras_no_dia.gt(0)]
            fig.add_scatter(x=censura.tempo_dias, y=censura.sem_correcao, mode="markers",
                            marker=dict(symbol="cross", color=cor), name=f"{grupo} · censura", legendgroup=grupo)
        fig.update_layout(title="Kaplan–Meier · IC 95%", xaxis_title="Dias desde 21/10/2026",
                          yaxis_title="Probabilidade de permanecer sem correção", yaxis_range=[-.03, 1.03])
        if fig.data:
            mostrar(fig, avisos, escopo)
        campos = ["grupo", "n", "eventos", "censurados", "mediana_dias", "ic95_mediana_inferior", "ic95_mediana_superior"]
        resumo = dados.drop_duplicates("grupo")[campos].copy()
        for coluna in campos[-3:]:
            resumo[coluna] = resumo[coluna].apply(lambda v: f"{v:g}" if pd.notna(v) else "Não estimável")
        tabela(resumo, "Medianas indisponíveis.")
        tabela(filtrar(logrank, {"analise": [escopo]}), "Log-rank indisponível para a seleção.")
    with st.expander("Fontes testadas na Sprint 1"):
        tabela(carregar_csv(DADOS / "rq3_teste_apis.csv"), "Tabela de fontes indisponível.")


def filtrar_rq3(km, lr, tipos):
    todos = set(GRUPOS.values())
    grupos = set(tipos)
    if "Distribuição Linux" in grupos:
        grupos.update(["comercial", "comunitario"])
    if km is not None:
        visiveis = km.grupo.isin(grupos)
        geral = km.grupo.eq("Geral") & (
            (km.analise.eq(PRINCIPAL) & todos.issubset(tipos))
            | (km.analise.eq(EXPLORATORIA) & ("Distribuição Linux" in tipos)))
        km = km[visiveis | geral]
    if lr is not None:
        pares = lr.grupo_a.isin(grupos) & lr.grupo_b.isin(grupos)
        lr = lr[pares | (lr.comparacao.eq("Multigrupo") & todos.issubset(tipos))]
    return km, lr


def main():
    st.set_page_config(page_title="LAB05 — Custo da correção do PHP2Shell", page_icon="🛡️", layout="wide")
    st.title("Corrigir o PHP2Shell custa desempenho?")
    st.caption("Experimento com WordPress, PHP 8.4.26 e 8.4.27. A RQ3 mede o tempo até a primeira correção publicada.")
    entrada = detectar_entrada(DADOS)
    bruto = carregar_csv(entrada)
    df = None
    avisos = []
    if bruto is not None:
        try:
            df, info = preparar(bruto)
            avisos = avisos_amostra(df, entrada)
            for aviso in avisos:
                st.warning(aviso)
            if info["legado"]:
                st.warning(LEGADO)
        except ValueError as erro:
            st.warning(str(erro))
    for aviso in aviso_k(RESULTADOS):
        st.warning(aviso)
    validacao = RESULTADOS / "validacao.md"
    if entrada.parent.name == "brutos" and validacao.is_file():
        texto = validacao.read_text(encoding="utf-8")
        if any(palavra in texto.lower() for palavra in ("bloque", "reprov", "inválid", "falha")):
            st.warning("A validação da coleta menciona problemas. Consulte o relatório antes de interpretar os resultados.")
        with st.expander("Relatório de validação da coleta"):
            st.markdown(texto)
    endpoints = sorted(df.endpoint.unique()) if df is not None else []
    tipos = list(dict.fromkeys(GRUPOS.values()))
    with st.sidebar:
        endpoint = st.multiselect("Endpoint", endpoints, default=endpoints)
        php = st.multiselect("Versão do PHP", ["8.4.26", "8.4.27"], default=["8.4.26", "8.4.27"])
        mitigacao = st.multiselect("Mitigação", [0, 1], default=[0, 1],
                                    format_func=lambda x: ["Desligada", "Ligada"][x])
        tratamentos = st.multiselect("Tratamento", list(TRATAMENTOS.Tratamento),
                                       default=list(TRATAMENTOS.Tratamento))
        metrica = st.selectbox("Métrica principal", list(METRICAS), index=2, format_func=rotulo)
        tipos = st.multiselect("Tipo de distribuidor", tipos, default=tipos)
    tratamentos = [t for i, t in enumerate(TRATAMENTOS.Tratamento)
                   if t in tratamentos and ["8.4.26", "8.4.27"][i//2] in php and i%2 in mitigacao]
    filtros = dict(endpoint=endpoint, php_version=php, mitigacao=mitigacao, tratamento=tratamentos)
    df = filtrar(df, filtros)
    bruto = filtrar(bruto, filtros)
    origem = assinatura(entrada) if df is not None else None
    d, a, e = [filtrar(fonte_desempenho(carregar_csv(RESULTADOS / f"rq1_rq2_{nome}.csv"), origem),
                       {"endpoint": endpoint, "metrica": [metrica]}) for nome in ["descritiva", "anova", "tost"]]
    d = filtrar(d, {"tratamento": tratamentos})
    a, e = filtrar_inferencia(a, e, tratamentos)
    raw = carregar_csv(DADOS / "rq3_correcoes.csv")
    if raw is not None and "grupo" in raw:
        raw = filtrar(raw.assign(tipo=raw.grupo.map(GRUPOS)), {"tipo": tipos})
    km, lr = filtrar_rq3(carregar_csv(RESULTADOS / "rq3_km_tabela.csv"),
                        carregar_csv(RESULTADOS / "rq3_logrank.csv"), tipos)
    baixo_poder = km is not None and km.baixo_poder.any()
    if raw is not None and {"incluir_analise", "evento", "tipo"} <= set(raw):
        eventos = raw[raw.incluir_analise.eq("sim")].groupby("tipo").evento.sum()
        baixo_poder = baixo_poder or len(eventos) < 2 or eventos.lt(5).any()
    if baixo_poder:
        st.warning(BAIXO_PODER)
    abas = st.tabs(["Visão geral", "RQ1 · Correção", "RQ2 · Mitigação", "RQ3 · Tempo até a correção",
                    "Testes", "Ameaças à validade", "Impacto", "Dados", "Poder e k"])
    with abas[0]:
        cartoes(df, metrica)
        st.subheader("Desenho do experimento (fatorial 2×2)")
        tabela(TRATAMENTOS[TRATAMENTOS.Tratamento.isin(tratamentos)], "Selecione os tratamentos.")
        for nome, efeito in [("RQ1 · Correção", "versao"), ("RQ2 · Mitigação", "mitigacao")]:
            sub = filtrar(e, {"contraste": [efeito]})
            numeros = sub.conclusao.value_counts().to_dict() if sub is not None and not sub.empty else {}
            st.write(f"**{nome}**", numeros or "Conclusão indisponível para a seleção.")
        geral = filtrar(km, {"analise": [PRINCIPAL], "grupo": ["Geral"]})
        if geral is not None and not geral.empty and pd.notna(geral.mediana_dias.iloc[0]):
            st.write(f"**RQ3 · Publicação da correção** · Mediana geral de {geral.mediana_dias.iloc[0]:g} dias.")
        else:
            st.write("**RQ3 · Publicação da correção** · Mediana geral indisponível para a seleção.")
        ev = carregar_csv(DADOS / "evidencias_php.csv")
        if ev is not None:
            with st.expander("Ramos do PHP em operação"):
                tabela(ev, "")
    with abas[1]:
        painel_desempenho(df, metrica, avisos, (d, a, e), 1)
    with abas[2]:
        painel_desempenho(df, metrica, avisos, (d, a, e), 2)
    with abas[3]:
        painel_rq3(raw, km, lr, avisos + ([BAIXO_PODER] if baixo_poder else []))
    with abas[4]:
        cartoes(df, metrica)
        for titulo, resultados in [("ANOVA", a), ("TOST", e), ("Log-rank", lr)]:
            st.subheader(titulo)
            tabela(resultados, "Resultados indisponíveis para a seleção.")
    with abas[5]:
        cartoes(df, metrica)
        caminho = RAIZ / "docs" / "ameacas_validade.md"
        if caminho.is_file():
            st.markdown(caminho.read_text(encoding="utf-8"))
        else:
            st.markdown("- **Conclusão:** Holm e aviso de baixo poder.\n"
                        "- **Interna:** ambiente e carga padronizados.\n"
                        "- **Construto:** métricas e unidades definidas por endpoint.\n"
                        "- **Externa:** conclusões restritas à configuração avaliada.")
    with abas[6]:
        cartoes(df, metrica)
        tabela(carregar_csv(RESULTADOS / "impacto.csv"), "disponível na Sprint 3")
        st.caption("O experimento não estima quantas instâncias estão expostas ou seriam afetadas no mundo real.")
    with abas[7]:
        cartoes(df, metrica)
        tabela(bruto, "CSV de desempenho indisponível ou sem linhas para os filtros.")
        if bruto is not None:
            st.download_button("Baixar CSV filtrado", bruto.to_csv(index=False).encode("utf-8-sig"),
                               file_name="lab05_filtrado.csv", mime="text/csv")

    with abas[8]:
        st.subheader("Quantas repetições (k) por tratamento?")
        poder = carregar_csv(RESULTADOS / "poder_k.csv")
        if poder is None:
            st.warning("Rode `python scripts/poder.py` para gerar resultados/poder_k.csv.")
        else:
            if (poder["origem"] == "assumido").any():
                st.warning("Valores provisórios: calculados com sigma ASSUMIDO, não com o piloto. Rode de novo com dados/piloto/.")
            alvo = st.slider("Poder alvo", 0.5, 0.99, 0.80, 0.01)
            coluna = st.selectbox(
                "Cenário",
                ["poder_equiv_efeito0", "poder_equiv_efeito2pct", "poder_detecta_5pct", "poder_detecta_10pct"],
                format_func=lambda c: {
                    "poder_equiv_efeito0": "Equivalência (TOST ±5%), efeito real 0",
                    "poder_equiv_efeito2pct": "Equivalência (TOST ±5%), efeito real +2%",
                    "poder_detecta_5pct": "Detectar diferença real de 5%",
                    "poder_detecta_10pct": "Detectar diferença real de 10%",
                }[c],
            )
            fig = go.Figure()
            for metrica, sub in poder.groupby("metrica"):
                fig.add_trace(go.Scatter(x=sub["k"], y=sub[coluna] * 100, mode="lines+markers", name=metrica))
            fig.add_hline(y=alvo * 100, line_dash="dash", line_color="#d62728", annotation_text=f"alvo {alvo:.0%}")
            fig.update_layout(
                xaxis_title="Repetições por tratamento (k)",
                yaxis_title="Poder (%)",
                yaxis_range=[0, 105],
                height=480,
            )
            mostrar(fig, avisos, "poder")
            k_min = {m: (int(s.loc[s[coluna] >= alvo, "k"].min()) if (s[coluna] >= alvo).any() else None) for m, s in poder.groupby("metrica")}
            st.write("**k mínimo por métrica:**", {m: (k if k else "> 40") for m, k in k_min.items()})



if __name__ == "__main__":
    main()

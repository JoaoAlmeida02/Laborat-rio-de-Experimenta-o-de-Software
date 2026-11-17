"""Dashboard do LAB05 (esqueleto da S01): custo da correção do PHP2Shell e tempo até a correção.

Rodar a partir da pasta LAB05:
    streamlit run app.py

Hoje mostra o que já existe (evidências, teste das fontes da RQ3, análise de poder).
As abas de resultados (RQ1, RQ2, RQ3), ameaças e impacto são preenchidas nas S02 e S03.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="LAB05 — Custo da correção do PHP2Shell", page_icon="🛡️", layout="wide")

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"
RESULTADOS = RAIZ / "resultados"

TRATAMENTOS = pd.DataFrame(
    {
        "Tratamento": ["T1", "T2", "T3", "T4"],
        "PHP": ["8.4.26 (vulnerável)", "8.4.26 (vulnerável)", "8.4.27 (corrigido)", "8.4.27 (corrigido)"],
        "session.upload_progress.enabled": ["1 (padrão)", "0 (mitigação)", "1 (padrão)", "0 (mitigação)"],
    }
)


@st.cache_data
def ler_csv(caminho):
    caminho = Path(caminho)
    return pd.read_csv(caminho) if caminho.exists() else None


def pendente(sprint, o_que):
    st.info(f"**Pendente ({sprint}):** {o_que}")


st.title("Corrigir o PHP2Shell custa desempenho?")
st.caption(
    "CVE-2026-109618 e CVE-2026-109619, corrigidas em 21/10/2026 (PHP 8.5.12, 8.4.27, 8.3.36 e 8.2.35). "
    "Nenhum exploit é executado: o estudo mede o custo da correção, não a falha."
)

abas = st.tabs(["Visão geral", "RQ1 · Correção", "RQ2 · Mitigação", "RQ3 · Tempo até a correção", "Poder e k", "Ameaças", "Impacto"])

with abas[0]:
    st.subheader("Desenho do experimento (fatorial 2×2)")
    st.dataframe(TRATAMENTOS, hide_index=True, width="stretch")
    st.markdown(
        "- **RQ1:** a correção (8.4.26 → 8.4.27) altera o desempenho do WordPress?\n"
        "- **RQ2:** a mitigação `session.upload_progress.enabled=0` altera o desempenho?\n"
        "- **RQ3:** quanto tempo distribuições, nuvens e painéis levaram para publicar a correção?"
    )
    ev = ler_csv(DADOS / "evidencias_php.csv")
    if ev is not None:
        st.subheader("Ramos do PHP em operação")
        st.dataframe(ev, hide_index=True, width="stretch")

with abas[1]:
    pendente("S02", "descritiva (mediana e IQR), ANOVA 2×2, TOST (±5%) e η² parcial da versão do PHP sobre rps, p50/p95/p99, memória e erro.")

with abas[2]:
    pendente("S02", "efeito da mitigação e da interação versão × mitigação.")

with abas[3]:
    st.subheader("Fontes testadas (S01)")
    apis = ler_csv(DADOS / "rq3_teste_apis.csv")
    if apis is None:
        st.warning("Rode `python scripts/testar_fontes_rq3.py` para gerar dados/rq3_teste_apis.csv.")
    else:
        st.dataframe(
            apis[["fonte", "veredito", "campo_data", "exemplo_data", "observacao"]],
            hide_index=True,
            width="stretch",
        )
        st.caption("serve = traz a data da correção · parcial = indica a correção mas sem data · referencia = data do CVE · sem_o_cve = não encontrou")
    pendente("S02", "curvas de Kaplan-Meier por grupo, tempo mediano até a correção e log-rank (distribuidor sem correção = censurado).")

with abas[4]:
    st.subheader("Quantas repetições (k) por tratamento?")
    poder = ler_csv(RESULTADOS / "poder_k.csv")
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
            template="plotly_white",
            height=480,
        )
        st.plotly_chart(fig, width="stretch")
        k_min = {m: (int(s.loc[s[coluna] >= alvo, "k"].min()) if (s[coluna] >= alvo).any() else None) for m, s in poder.groupby("metrica")}
        st.write("**k mínimo por métrica:**", {m: (k if k else "> 40") for m, k in k_min.items()})

with abas[5]:
    pendente("S02", "ameaças à validade (conclusão, interna, construto, externa) com mitigações, vindas de docs/ameacas_validade.md.")

with abas[6]:
    pendente("S03", "tabela de impacto cruzando o custo da correção e os dias até a correção com números públicos (W3Techs, instâncias expostas).")

# LAB05 — Ameaças à Validade (Sprint 2)

Este documento lista as ameaças dos quatro tipos para as duas partes do estudo: o **experimento** (RQ1 e RQ2, custo da correção e da mitigação) e os **dados de operação** (RQ3, tempo até a correção). Cada ameaça traz a mitigação e a situação:

- ✅ **aplicada:** já está no código ou nos dados.
- 🔄 **planejada:** será feita até a S03.
- ⚠️ **residual:** não há como eliminar; entra nas limitações do documento final.

Referências: [`docs/proposta.md`](proposta.md) (seção 11, primeira lista), [`scripts/executar_benchmarks.py`](../scripts/executar_benchmarks.py), [`scripts/poder.py`](../scripts/poder.py), [`scripts/coleta_correcoes.py`](../scripts/coleta_correcoes.py).

---

## 1. Validade de conclusão

*As conclusões estatísticas estão corretas?*

| # | Ameaça | RQ | Mitigação | Situação |
|---|---|---|---|---|
| C1 | **Poder insuficiente para o TOST.** O `resultados/poder_k.csv` atual usa variabilidade **assumida** (σ = 0,03), porque o piloto ainda não foi versionado. Se o ruído real for maior, k = 5 pode não bastar para concluir equivalência | RQ1, RQ2 | Rodar o piloto, versionar em `dados/piloto/` e refazer o `poder.py` com o σ medido (o script já usa o limite superior de um IC de 80% para não subestimar k) | 🔄 planejada (antes da coleta completa) |
| C2 | **Comparações múltiplas.** São 2 fatores + interação, em 3 endpoints e em várias métricas (rps, p50, p95, p99, memória, erro). Muitos testes aumentam a chance de um falso positivo | RQ1, RQ2 | Definir antes da análise uma métrica principal (p95 da rota geral) e corrigir as demais com Holm | 🔄 planejada |
| C3 | **Pressupostos da ANOVA.** Latências são assimétricas e podem ter variância diferente entre tratamentos | RQ1, RQ2 | Análise sobre o log da métrica; se os resíduos falharem nos pressupostos, usar ART-ANOVA | 🔄 planejada |
| C4 | **Percentis altos instáveis.** O p99 de uma janela de 60 s depende de poucas requisições lentas | RQ1, RQ2 | O `poder.py` escolhe k pela métrica mais ruidosa (em geral o p99); na análise, sugerimos reportar o p99 e decidir pelo p95 (ver C2) | ✅ aplicada (no cálculo de k) / 🔄 decisão |
| C5 | **Amostra pequena na RQ3.** Entram 14 distribuidores, com 13 eventos e 1 censura. Nuvem e hospedagem têm dois eventos cada. | RQ3 | Reportar Kaplan–Meier e ICs da mediana. Sinalizar baixo poder do log-rank na comparação principal (Linux, nuvem e hospedagem) e na exploratória (Linux comunitário e comercial). Tratar os testes como não conclusivos. | ✅ aplicada na apresentação dos resultados |
| C6 | **Empates em zero dias.** Com resolução de dia, 10 dos 14 distribuidores corrigiram no próprio dia 21/10. A curva cai quase toda no dia 0 e diferenças de horas desaparecem | RQ3 | Registrar também a data da **última** correção (cobertura completa), que varia mais: o Red Hat leva 21 dias e o Rocky 23 | ✅ aplicada (colunas `data_ultima_correcao` e `dias_ate_ultima_correcao`) |

## 2. Validade interna

*A diferença observada é mesmo causada pelo tratamento?*

| # | Ameaça | RQ | Mitigação | Situação |
|---|---|---|---|---|
| I1 | **Ordem dos tratamentos.** Aquecimento da máquina, atualizações em segundo plano ou cache do disco podem favorecer quem roda por último | RQ1, RQ2 | Ordem aleatória com semente fixa (42) | ✅ aplicada |
| I2 | **Estado residual entre execuções.** Sessões, cache do OPcache e do banco de uma repetição afetando a seguinte | RQ1, RQ2 | `docker compose down -v` a cada repetição, banco recriado com 50 posts determinísticos, 30 s de aquecimento descartados | ✅ aplicada |
| I3 | **Disputa de CPU entre a carga e o servidor.** Os contêineres usam **cotas** de CPU (`cpus: "2.0"`), e não **núcleos fixos** (`cpuset`) como previa a proposta. O k6 e o PHP-FPM podem disputar os mesmos núcleos | RQ1, RQ2 | Fixar núcleos com `cpuset` (ex.: k6 em 0–1, PHP-FPM em 2–3) ou, no mínimo, registrar o uso de CPU do host durante cada execução | 🔄 planejada (combinar com o Vitor) |
| I4 | **Ruído da máquina.** Windows + Docker Desktop + WSL2 adicionam uma camada de virtualização; antivírus, indexação e modo de energia variam ao longo do dia | RQ1, RQ2 | Registrar o ambiente (`ambiente_maquina.json`); coletar com o notebook na tomada, em modo desempenho e sem outros programas; marcar no log execuções feitas fora dessas condições | 🔄 planejada |
| I5 | **Diferenças entre as imagens além da correção.** `php:8.4.26-fpm` e `php:8.4.27-fpm` podem diferir em outras correções de bugs ou na imagem base | RQ1 | As imagens são fixadas por versão; a diferença medida é atribuída à **release** 8.4.27 como um todo, e não a um único commit (ver construto K1) | ⚠️ residual |
| I6 | **Exclusões na RQ3 podem enviesar o resultado.** Alpine (corrigido, mas sem data) e Docker Hub (sem data de primeira publicação) ficam fora. Se justamente os mais lentos forem os de dado incerto, o ecossistema parece mais rápido do que é | RQ3 | Google Cloud e Plesk foram verificados nas fontes oficiais e entraram na análise; reportar no documento quais ficaram fora e por quê | ✅ aplicada / ⚠️ residual |

## 3. Validade de construto

*As métricas medem mesmo o que queremos medir?*

| # | Ameaça | RQ | Mitigação | Situação |
|---|---|---|---|---|
| K1 | **"Custo da correção" = custo da release.** A 8.4.27 traz a correção do PHP2Shell e outras mudanças | RQ1 | Formular a conclusão como "atualizar de 8.4.26 para 8.4.27 custa X", que é a decisão real de quem opera o PHP | ✅ aplicada (na formulação da RQ1) |
| K2 | **Carga sintética.** O k6 com 10 usuários virtuais e 3 endpoints não representa o tráfego de um site real (cache de página, mídia, plugins) | RQ1, RQ2 | Usar um WordPress real (6.9.4) com conteúdo determinístico e três tipos de rota; a carga exercita de fato o recurso afetado pela mitigação (campo `PHP_SESSION_UPLOAD_PROGRESS` no upload) | ✅ aplicada / ⚠️ residual |
| K3 | **Lei de Goodhart.** Olhar só a média ou o rps esconderia uma piora no pior caso | RQ1, RQ2 | Medir p50, p95 e p99 e a taxa de erro, não só a média | ✅ aplicada |
| K4 | **Margem de equivalência arbitrária.** ±5% é uma escolha do grupo; com outra margem a conclusão pode mudar | RQ1, RQ2 | Justificar a margem (variação típica de releases de manutenção) e reportar também a menor margem que o k escolhido consegue confirmar (já calculada pelo `poder.py`) | ✅ aplicada / 🔄 justificar no texto |
| K5 | **Cada fonte tem um significado de "data".** Ubuntu: publicação do aviso USN. Red Hat e Rocky: data da release do RHSA/RLSA. OSV (AlmaLinux, SUSE): `published` do aviso. Fedora: chegada ao repositório estável (`date_stable`). Páginas manuais: data do boletim. Nem sempre é o momento em que o pacote ficou disponível no espelho do usuário | RQ3 | Usar sempre a data do **aviso do próprio distribuidor** (nunca o `published` da CVE no OSV, que é a data da CVE); documentar o campo de cada fonte em `rq3_fontes.csv` | ✅ aplicada |
| K6 | **Divulgação coordenada.** Distribuições recebem aviso antecipado (embargo) do projeto PHP. Corrigir "no dia 0" mede a **participação na divulgação coordenada**, não a velocidade de reação depois do anúncio | RQ3 | Interpretar o dia 0 dessa forma no texto e discutir que quem ficou fora do embargo (nuvens, painéis) aparece depois | 🔄 planejada (texto) |
| K7 | **"Primeira correção" ≠ "todos protegidos".** Um distribuidor corrige um produto no dia 0 e outro semanas depois (Red Hat: 21/10 a 11/11; AlmaLinux: até 11/11; Rocky: até 13/11). Há também produtos que **nunca** serão corrigidos (Amazon Linux: 2 com "No Fix Planned"; Azure Windows: fim de vida) | RQ3 | Evento principal = 1ª correção, mais as colunas de última correção e de produtos pendentes | ✅ aplicada |
| K8 | **Ausência de evidência ≠ ausência de correção.** O Azure está censurado porque não encontramos data publicada de conclusão; ele pode ter corrigido sem anunciar | RQ3 | Marcar a situação como `sem_correcao_publicada` (e não "não corrigiu") e registrar o link e a data de acesso | ✅ aplicada |
| K9 | **Data aproximada.** O boletim da AWS não informa quando o Elastic Beanstalk foi corrigido; usamos 30/10 (última atualização do boletim) como limite superior | RQ3 | Coluna `precisao_data = limite_superior`; análise de sensibilidade com a AWS no dia 0 e no dia 9 | ✅ aplicada / 🔄 sensibilidade |
| K10 | **Fuso horário.** As datas automáticas são tomadas em UTC. Um aviso do Rocky às 00:08 UTC de 22/10 foi publicado na noite de 21/10 nas Américas e conta como 1 dia. As notas do Google estão no fuso do Pacífico (EUA) | RQ3 | Usar UTC nas fontes automáticas, registrar o fuso das manuais e citar o caso no texto | ✅ aplicada / ⚠️ residual |
| K11 | **Fontes que se corrigem ou se contradizem.** A nota do App Engine de 21/10 foi marcada depois pelo próprio Google como **incorreta**. Posts do fórum do Plesk diziam que não haveria correção para PHP 8.1 ou anterior, mas o changelog oficial mostra o backport em 21/10 | RQ3 | Usar só fontes **oficiais** do distribuidor (nunca fóruns ou blogs de terceiros) e, quando a própria fonte se corrige, usar a versão corrigida e registrar isso na observação | ✅ aplicada |

## 4. Validade externa

*Os resultados valem fora do nosso cenário?*

| # | Ameaça | RQ | Mitigação | Situação |
|---|---|---|---|---|
| E1 | **Uma máquina, um sistema.** Os números de desempenho valem para a máquina do Vitor com Docker Desktop no Windows; um servidor Linux dedicado pode ter outro comportamento | RQ1, RQ2 | Reportar o ambiente completo; falar em diferença **relativa** (%) entre versões, que tende a se manter melhor que o valor absoluto | ⚠️ residual |
| E2 | **Um ramo e uma aplicação.** Só PHP 8.4 e WordPress. Outros ramos (8.2, 8.3, 8.5) e frameworks (Laravel, Drupal) podem reagir diferente | RQ1, RQ2 | Opcional da S02: repetir na linha 8.3 (8.3.35 × 8.3.36) | 🔄 opcional |
| E3 | **Amostra de distribuidores por conveniência.** Os 16 distribuidores foram escolhidos por serem conhecidos e terem fontes públicas, não por sorteio. Distribuidores menores e hospedagens compartilhadas não estão representados | RQ3 | Não generalizar para "todo o ecossistema"; falar em "principais distribuições e plataformas" | ⚠️ residual |
| E4 | **Disponível ≠ instalado.** A RQ3 mede quando a correção ficou **disponível**, não quando os servidores foram de fato atualizados. Usar esse tempo como "tempo de exposição" subestima a exposição real | RQ3 | Deixar explícito no impacto (S03) o que **não** dá para afirmar | 🔄 planejada (S03) |
| E5 | **Estimativa de sites expostos.** O W3Techs só enxerga a versão do PHP em sites que a revelam (ex.: cabeçalho `X-Powered-By`); a estimativa de ~44,6% de sites em ramos sem correção pode estar enviesada | Impacto | Citar como estimativa, com fonte e data de acesso | ✅ aplicada |

---

## Resumo do que falta

1. **Antes da coleta completa (Vitor e João):** rodar e versionar o piloto e recalcular k com o σ medido (C1); decidir sobre `cpuset` (I3).
2. **Análise (João):** métrica principal e correção de Holm (C2); log-rank só entre comunitário e comercial (C5); sensibilidade da AWS (K9).
3. **Texto final (S03):** interpretação do dia 0 como divulgação coordenada (K6) e limites do impacto (E4).

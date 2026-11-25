# LAB05 — Custo da Correção do PHP2Shell e Tempo até a Correção

Repositório do experimento controlado (fatorial 2×2) e da coleta de dados de operação do **LAB05** (Laboratório de Experimentação de Software — PUC Minas).

> **Nota ética:** nenhum exploit das CVEs do PHP2Shell (CVE-2026-109618 / CVE-2026-109619 / CVE-2026-115560) é escrito ou executado, nem localmente. Os testes de carga atingem exclusivamente os contêineres locais do grupo.

---

## Ambiente e piloto

### Tratamentos (fatorial 2×2)

| Tratamento | Versão PHP | `MITIGACAO` | `session.upload_progress.enabled` | Descrição |
|---|---|---:|---|---|
| **T1** | `8.4.26` | `0` | `On` (`1`, padrão) | Vulnerável, mitigação desligada |
| **T2** | `8.4.26` | `1` | `Off` (`0`) | Vulnerável, mitigação ligada |
| **T3** | `8.4.27` | `0` | `On` (`1`, padrão) | Corrigido, mitigação desligada |
| **T4** | `8.4.27` | `1` | `Off` (`0`) | Corrigido, mitigação ligada |

### Imagens com versões fixadas

- PHP-FPM: `php:8.4.26-fpm` e `php:8.4.27-fpm` (com WP-CLI `2.11.0`, `opcache`, `mysqli`, `gd`, `zip`, `intl`, `exif`, `mbstring`)
- Nginx: `nginx:1.27.5-alpine`
- MariaDB: `mariadb:11.4.13`
- WordPress: `wordpress:6.9.4-fpm` (arquivos copiados para volume compartilhado + mu-plugin benigno de sessão e upload)
- k6 (fallback em contêiner): `grafana/k6:1.0.0`

Todos os serviços usam limites fixos de CPU e memória (`php`: 2 CPUs / 512 MB; `nginx`: 1 CPU / 256 MB; `mariadb`: 1 CPU / 512 MB) e parâmetros idênticos de `php.ini` e `www.conf` (`pm = static`, `pm.max_children = 16`, `memory_limit = 256M`, OPcache fixo).

### Pré-requisitos (Windows + Docker Desktop + WSL2)

1. **Docker Desktop** em execução com backend **WSL2** habilitado (`docker compose` v2).
2. **Python 3.10+** instalado no PATH. Opcionalmente, instale as dependências do projeto (inclui `psutil` para leitura de núcleos físicos/RAM):
   ```powershell
   cd LAB05
   pip install -r requirements.txt
   ```
3. **k6** (opcional localmente):
   - Se o executável `k6` estiver instalado no PATH (ex.: `winget install k6`), o script usa o `k6` local automaticamente.
   - Se o `k6` **não** estiver instalado localmente, `scripts/executar_benchmarks.py` executa automaticamente a imagem fixada `grafana/k6:1.0.0` via Docker (`--k6-modo auto`).

### Como subir um tratamento manualmente

A partir da pasta `LAB05/ambiente/`:

- **Windows PowerShell (exemplo com T1 — PHP 8.4.26, mitigação desligada):**
  ```powershell
  cd LAB05/ambiente
  $env:PHP_VERSION="8.4.26"; $env:MITIGACAO="0"; docker compose up -d --build
  ```
- **WSL2 / Git Bash (exemplo com T4 — PHP 8.4.27, mitigação ligada):**
  ```bash
  cd LAB05/ambiente
  PHP_VERSION=8.4.27 MITIGACAO=1 docker compose up -d --build
  ```

Após os healthchecks e o serviço `setup` concluírem (criando automaticamente o WordPress e 50 posts determinísticos):
- Página inicial do WordPress: `http://localhost:8080/`
- API REST de posts: `http://localhost:8080/wp-json/wp/v2/posts`
- Verificação do endpoint benigno de sessão/upload e da diretiva ativa: `http://localhost:8080/?lab05_upload=1`
- Conferência nos logs do PHP-FPM (`php -i` no startup):
  ```powershell
  docker compose logs php
  ```
- Para derrubar e limpar o volume do banco de dados:
  ```powershell
  docker compose down -v
  ```

### Como rodar o piloto

A partir da pasta `LAB05/` (com o Docker Desktop aberto):

- **Piloto completo (2 repetições × 4 tratamentos = 8 execuções em ordem aleatória com semente 42):**
  ```powershell
  python scripts/executar_benchmarks.py --piloto
  ```
- **Smoke test rápido (1 tratamento, 1 repetição, 5 s aquecimento + 10 s medição):**
  ```powershell
  python scripts/executar_benchmarks.py --k 1 --tratamentos T1 --aquecimento 5 --medicao 10 --vus 2 --saida dados/piloto/smoke
  ```
- **Dry-run (valida o plano embaralhado e gera `ambiente_maquina.json` sem subir contêineres):**
  ```powershell
  python scripts/executar_benchmarks.py --piloto --dry-run
  ```

### Onde ficam os resultados

Por padrão, em `LAB05/dados/piloto/`:
- `dados/piloto/piloto.csv`: CSV consolidado com 4 linhas por execução (`geral`, `home`, `rest_posts`, `sessao_upload`) e colunas `execucao_id, ordem, tratamento, php_version, mitigacao, repeticao, endpoint, rps, p50_ms, p95_ms, p99_ms, taxa_erro, mem_php_media_mb, mem_php_pico_mb, timestamp_inicio, timestamp_fim`. (`taxa_erro` é a fração de requisições com falha, de `0.0` a `1.0`.)

## Sprint 2 — análise estatística e dashboard

Execute a partir de `LAB05`, com Python 3.10 ou superior no PATH:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/analise_rq1_rq2.py --entrada dados/piloto/piloto.csv --saida resultados
python scripts/analise_rq3.py --entrada dados/rq3_correcoes.csv --saida resultados
python scripts/graficos.py --entrada dados/piloto/piloto.csv --entrada-rq3 dados/rq3_correcoes.csv --saida resultados
python -m streamlit run app.py
```

- **RQ1/RQ2.** Gera `rq1_rq2_descritiva.csv`, `rq1_rq2_anova.csv`, `rq1_rq2_tost.csv` e `rq1_rq2_resumo.md`. Use o p ajustado por Holm para decisões. A ANOVA usa SS tipo II, com log para RPS e latências positivas. O ART alinha cada efeito por médias de células, ranqueia os valores alinhados e testa o termo correspondente. O η² parcial do ART descreve a escala dos postos. O TOST mede diferenças de médias na unidade original com IC nominal de 90%. A margem padrão é ±5% da mediana de T1 nos contrastes simples e da mediana conjunta do nível de referência nos efeitos principais. Um teste separado avalia evidência de diferença além da margem. Ambos recebem Holm em famílias separadas. Sem evidência suficiente, a conclusão é inconclusiva.
- **RQ3.** Gera `rq3_km_tabela.csv`, `rq3_logrank.csv` e `rq3_resumo.md`. A curva mostra a probabilidade de continuar sem a primeira correção desde 21/10/2026. A análise principal reúne distribuições Linux e as compara com nuvem e hospedagem. A exploratória compara os subgrupos Linux. Campos vazios de mediana ou IC representam limites não estimáveis. Menos de cinco eventos em um grupo sinaliza baixo poder do log-rank.
- **Gráficos.** Gera PNGs a 200 dpi com distribuições, interação, intervalos do TOST e curvas Kaplan–Meier. Use os mesmos valores de `--alfa` e `--margem` na análise de desempenho e nos gráficos.
- **Piloto.** A entrada de piloto ou menos de cinco observações válidas em alguma célula sinaliza ausência de poder para conclusões. Se o piloto estiver ausente, execute a RQ3 e os testes sintéticos em memória. O script de gráficos gera as curvas da RQ3 mesmo sem desempenho. O CSV legado sem `status` tem as linhas tratadas como ok com aviso. Linhas com métricas ausentes são excluídas e contabilizadas. O k do arquivo de poder atual é provisório.

Após validar `dados/brutos/dados.csv`, reexecute:

```powershell
python scripts/analise_rq1_rq2.py --entrada dados/brutos/dados.csv --saida resultados
python scripts/analise_rq3.py --entrada dados/rq3_correcoes.csv --saida resultados
python scripts/graficos.py --entrada dados/brutos/dados.csv --entrada-rq3 dados/rq3_correcoes.csv --saida resultados
python -m streamlit run app.py
```

O dashboard dá preferência ao CSV bruto. Os filtros selecionam as tabelas e os pontos visíveis. Os p ajustados preservam as famílias completas calculadas pelos scripts.
- `dados/piloto/brutos_k6/`: JSON bruto de cada execução (`ord01_T...json`) com o resumo estruturado da fase de medição e todas as métricas brutas do k6.
- `dados/piloto/ambiente_maquina.json`: metadados da máquina (CPU, núcleos, RAM, SO, versões do Python, Docker, Docker Compose, k6 e imagens fixadas).
- `dados/piloto/execucao.log`: log completo de progresso e eventuais erros de execução.

# LAB02 — Sprint 01: Setup do Ambiente e Coleta de Métricas Estáticas

Este diretório contém os artefatos da **Sprint 01 do LAB02** da disciplina de *Laboratório de Experimentação de Software* (Engenharia de Software).

O objetivo desta issue é disponibilizar o ambiente de medição estática de código (RQ3) e o script automatizado de extração de métricas de qualidade, manutenibilidade, tamanho e duplicação para os trials do experimento controlado.

---

## 1. Pré-requisitos

- **Python 3.10 ou superior** (com `pip`)
- **Node.js 18 ou superior** (com `npm` / `npx`)

---

## 2. Instalação e Configuração

### 2.1. Ambiente Virtual Python e Radon

Recomenda-se a utilização de um ambiente virtual (`venv`):

```bash
# 1. Criação do ambiente virtual (opcional, mas recomendado)
python -m venv .venv

# 2. Ativação do ambiente virtual
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux / macOS:
source .venv/bin/activate

# 3. Instalação das dependências Python fixadas
pip install -r requirements.txt
```

> **Nota:** Caso prefira instalar manualmente sem requirements.txt:
> ```bash
> pip install radon==6.0.1
> ```

### 2.2. Instalação do jscpd (Detector de Duplicação)

Instale o `jscpd` globalmente via npm:

```bash
npm install -g jscpd
```

> **Dica:** O script `collect_metrics.py` possui fallback automático para `npx -y jscpd` caso o pacote global não esteja no `PATH`.

---

## 3. Como Verificar a Instalação

Execute os comandos abaixo no terminal para validar que as ferramentas estão prontas para uso:

```bash
# Verificar versão do Radon
python -c "import radon; print(f'Radon OK: versão {radon.__version__}')"

# Verificar versão do jscpd
jscpd -V
# ou via npx:
npx jscpd -V
```

---

## 4. Organização das Subpastas de Trial em `dados/`

Durante a execução da **Sprint 02 (S02)**, cada trial realizado por um participante deve ser salvo em uma subpasta exclusiva dentro de `dados/`.

### 4.1. Estrutura de Diretórios e Nomenclatura

O nome da subpasta é utilizado como identificador único (`trial_id`):

```text
LAB02/Lab02S01/dados/
  ├── .gitkeep
  ├── exemplo_kata1_vitor_com_ia/          <- subpasta do trial (trial_id)
  │     ├── metadata.json                 <- metadados do trial
  │     └── solucao.py                    <- código Python implementado pelo participante
  ├── vitor_kata2_rota_entregador_com_ia/
  │     ├── metadata.json
  │     └── solucao.py
  └── ...
```

### 4.2. Formato do `metadata.json`

Cada subpasta de trial **obrigatoriamente** deve conter um arquivo `metadata.json` com os seguintes campos:

```json
{
  "kata": "kata1_validador_cofre",
  "participante": "Vitor",
  "tratamento": "com_ia"
}
```

- `kata`: Nome identificador do kata (`kata1_validador_cofre`, `kata2_rota_entregador`, `kata3_compressor_log`, `kata4_escalonador_plantao`).
- `participante` (ou `pessoa`): Nome do integrante do grupo.
- `tratamento`: Condição experimental (`com_ia` ou `sem_ia`).

> **Importante:**
> - Pastas de gabarito (`gabaritos/`) e templates de referência (`katas/*/solucao.py`) **NÃO** são analisados nas métricas dos participantes.
> - Arquivos de testes de aceitação (`test_*.py`) presentes nas pastas de trial são automaticamente ignorados pelo script de métricas para não distorcer as medições do código desenvolvido pelo participante.

---

## 5. Execução do Script de Coleta de Métricas

O script `collect_metrics.py` varre as subpastas de `dados/`, calcula as métricas estáticas via API do Radon e CLI do jscpd, e exporta um arquivo consolidado em formato CSV.

### 5.1. Comandos de Uso

```bash
# Execução padrão (lê pasta 'dados' e gera 'metrics.csv')
python collect_metrics.py

# Execução com parâmetros customizados e modo detalhado (verbose)
python collect_metrics.py --dados-dir dados --output metrics.csv --verbose
```

### 5.2. Opções da Linha de Comando

| Argumento | Tipo | Padrão | Descrição |
|---|---|---|---|
| `--dados-dir` | Texto | `dados` | Diretório onde estão armazenadas as subpastas de cada trial |
| `--output` | Texto | `metrics.csv` | Caminho do arquivo CSV de saída consolidado |
| `-v`, `--verbose` | Flag | `False` | Exibe o log detalhado de cada trial processado no console |

---

## 6. Dicionário de Dados do CSV de Saída (`metrics.csv`)

O arquivo CSV gerado possui uma linha por trial executado e as seguintes colunas:

| Coluna | Tipo | Ferramenta | Descrição |
|---|---|---|---|
| `trial_id` | String | Sistema | Nome da subpasta do trial. É a **chave primária** usada para fazer join com os dados de RQ1/RQ2 do `cronometro.py` (`resultados.csv`) na análise da S03. |
| `kata` | String | `metadata.json` | Nome do kata implementado no trial. |
| `participante` | String | `metadata.json` | Nome do integrante que realizou o trial. |
| `tratamento` | String | `metadata.json` | Condição experimental: `com_ia` (com assistente IA) ou `sem_ia` (manual). |
| `loc` | Inteiro | `radon.raw` | Total de Linhas de Código brutas (*Lines of Code*). |
| `lloc` | Inteiro | `radon.raw` | Linhas Lógicas de Código executáveis (*Logical Lines of Code*). |
| `sloc` | Inteiro | `radon.raw` | Linhas de Código Fonte efetivas, excluindo comentários e linhas em branco (*Source Lines of Code*). |
| `comentarios` | Inteiro | `radon.raw` | Quantidade de linhas com comentários de código. |
| `linhas_brancas` | Inteiro | `radon.raw` | Quantidade de linhas em branco. |
| `cc_media` | Float | `radon.complexity` | Complexidade Ciclomática média de McCabe calculada sobre todas as funções e métodos do trial. |
| `cc_max` | Inteiro | `radon.complexity` | Complexidade Ciclomática máxima encontrada entre as funções do trial. |
| `cc_total` | Inteiro | `radon.complexity` | Soma total da Complexidade Ciclomática de todas as funções do trial. |
| `n_funcoes` | Inteiro | `radon.complexity` | Quantidade de funções e métodos identificados e analisados no trial. |
| `indice_manutenibilidade` | Float | `radon.metrics` | Índice de Manutenibilidade (*Maintainability Index* - MI) em escala de 0 a 100. Quanto maior, mais manutenível é o código. |
| `duplicacao_pct` | Float | `jscpd` | Porcentagem (%) de duplicação de código detectada pelo `jscpd` (parâmetros calibrados: `--min-lines 5 --min-tokens 20`). |

---

## 7. Integração e Próximos Passos (Sprint 02 e Sprint 03)

1. **Sprint 02 (Execução dos Trials):** Os participantes realizam as sessões com auxílio do `cronometro.py`, gerando os tempos e taxas de acerto em `dados/resultados.csv` e salvando o código implementado em `dados/<trial_id>/`.
2. **Sprint 03 (Análise Estatística):** Executa-se `collect_metrics.py` para gerar `metrics.csv`. Em seguida, realiza-se o merge entre `metrics.csv` e `resultados.csv` usando `trial_id` como chave para testar as hipóteses de RQ1 (tempo), RQ2 (taxa de sucesso nos testes) e RQ3 (complexidade, manutenibilidade e duplicação).

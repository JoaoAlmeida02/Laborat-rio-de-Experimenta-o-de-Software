# Lab03: Mineração de Métricas DORA

## 1. Instalar

Requer Python 3.10 ou superior.

```bash
cd LAB03
pip install -r requirements.txt
```

## 2. Configurar o token

Crie o arquivo `LAB03/.env` com um token do GitHub (Settings → Developer settings → Personal access tokens; nenhum escopo é necessário):

```
GITHUB_TOKEN=ghp_seu_token
```

## 3. Rodar a coleta

```bash
python -m pipeline.releases --inicio 2025-01-01 --fim 2025-12-31 --repos psf/requests astral-sh/ruff
```

Os resultados ficam em `LAB03/data/`. Se a execução for interrompida, rode o mesmo comando de novo: os repositórios já coletados não são baixados outra vez.

## 4. Rodar os testes

```bash
python -m pytest --cov=metricas
```

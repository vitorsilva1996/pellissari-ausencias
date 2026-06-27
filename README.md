# Sistema de Gestão de Ausências — Pellissari Fluidez Digital

Sistema web para controle de férias e day off dos colaboradores, substituindo o controle manual em planilha.

**Stack:** Python 3.11 · Flask · MySQL 8.0 · Docker · GitHub Actions

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) ou Docker Engine + Docker Compose (Linux/WSL2)
- Git

---

## Rodando o projeto localmente (desenvolvimento)

### 1. Clone o repositório e configure o ambiente

```bash
git clone https://github.com/<org>/pellissari-ausencias.git
cd pellissari-ausencias
cp .env.example .env
```

Edite o arquivo `.env` com as credenciais desejadas para o ambiente local.

### 2. Suba os containers

```bash
docker compose up --build
```

Na primeira execução, o Docker irá baixar as imagens e instalar as dependências. Aguarde até ver a mensagem do Flask indicando que o servidor está rodando.

A aplicação estará disponível em: **http://localhost:5000**

### 3. Crie as tabelas no banco de dados

Em outro terminal (com os containers rodando):

```bash
docker compose exec app flask db init      # apenas na primeira vez
docker compose exec app flask db migrate -m "estrutura inicial"
docker compose exec app flask db upgrade
```

### 4. Parando os containers

```bash
docker compose down           # para e remove os containers (dados persistem nos volumes)
docker compose down -v        # remove também os volumes (apaga o banco)
```

---

## Comandos úteis

| Comando | Descrição |
|---|---|
| `docker compose up --build` | Sobe o ambiente (rebuild da imagem) |
| `docker compose up -d` | Sobe em background |
| `docker compose logs -f app` | Acompanha logs da aplicação |
| `docker compose exec app flask shell` | Abre o shell interativo do Flask |
| `docker compose exec app flask db migrate -m "descrição"` | Gera nova migration |
| `docker compose exec app flask db upgrade` | Aplica migrations pendentes |
| `docker compose exec app python scripts/importar_planilha.py` | Importa dados legados da planilha |

---

## Estrutura do projeto

```
pellissari-ausencias/
├── app/
│   ├── __init__.py            # Application factory (Flask)
│   ├── models.py              # Modelos SQLAlchemy
│   ├── auth/                  # Login, logout, sessão
│   ├── ferias/                # Rotas e lógica de férias
│   ├── dayoff/                # Rotas e lógica de day off
│   ├── colaboradores/         # Cadastro de colaboradores
│   ├── calendario/            # Calendário unificado
│   ├── painel/                # Painel gerencial
│   ├── notificacoes/          # E-mails e alertas
│   └── templates/             # HTML (Jinja2) + arquivos estáticos
├── migrations/                # Scripts Alembic gerados automaticamente
├── scripts/                   # Utilitários (ex: importação da planilha legada)
├── tests/                     # Testes automatizados (pytest)
├── nginx/                     # Configuração do Nginx (produção)
├── .github/workflows/         # Pipelines CI/CD (GitHub Actions)
├── docker-compose.yml         # Desenvolvimento local
├── docker-compose.prod.yml    # Produção (inclui Nginx)
├── Dockerfile
├── .env.example               # Modelo de variáveis de ambiente (versionado)
├── .env                       # Valores reais — NÃO versionado
├── config.py                  # Configurações development / production
├── requirements.txt
├── run.py
└── README.md
```

---

## Perfis de acesso

| Perfil | Permissões |
|---|---|
| **Colaborador** | Ver e solicitar próprias férias/day off; calendário da equipe |
| **Gestor** | + Aprovar/reprovar (1ª instância); painel da equipe |
| **RH** | + Aprovar/reprovar (2ª instância); cadastrar colaboradores; relatórios |
| **Diretoria** | Somente visualização: relatórios, painel e calendário |

---

## Estratégia de branches

| Branch | Finalidade |
|---|---|
| `main` | Código em produção — protegida, aceita apenas PR aprovado |
| `develop` | Integração de funcionalidades |
| `feature/<nome>` | Nova funcionalidade — criada a partir de `develop` |
| `hotfix/<nome>` | Correção urgente — criada a partir de `main` |

---

## Produção

```bash
# Sobe todos os serviços (app + db + nginx) em background
docker compose -f docker-compose.prod.yml up -d --build
```

O Nginx escuta na porta **80** e faz proxy para o Gunicorn rodando na porta 5000 (interna).

# Estratégia de Branches (Git Flow)

Este projeto adota um fluxo de branches rígido para separar os códigos de referência da Receita Federal, o desenvolvimento ativo em Python/FastAPI, a homologação em Docker e a versão de produção.

## Branches Permanentes

| Branch | Finalidade | Regra de Proteção |
| :--- | :--- | :--- |
| `originals` | Cópia fiel dos repositórios oficiais da RFB (Java/Go) em `references/` | Somente leitura para consulta de regras de negócio; nunca recebe código Python. |
| `development` | Desenvolvimento ativo, refatoração e testes unitários/TDD (`backend/`, `frontend/`) | Branch padrão de trabalho diário (`feature/*` -> `development`). |
| `staging` | Homologação integrada simulando produção via `docker compose up --build` | Recebe merges de `development` para validação E2E antes da release. |
| `main` | Versão estável pronta para deploy em VPS | Recebe merges apenas de `staging` após validação completa. |

## Comandos de Configuração Inicial

### Windows (PowerShell)
```powershell
# Apenas estrutura de branches
.\scripts\setup_git_flow.ps1

# Estrutura + clone dos repositórios oficiais da RFB na branch originals
.\scripts\setup_git_flow.ps1 -ImportRfbRepos
```

### Linux / macOS (Bash)
```bash
chmod +x scripts/setup_git_flow.sh
IMPORT_RFB_REPOS=true ./scripts/setup_git_flow.sh
```

## Fluxo de Trabalho Diário

```bash
# 1. Criar feature a partir de development
git checkout development
git checkout -b feature/simples-calculo-ibs-cbs

# 2. Consultar código original sem poluir a feature (se necessário)
git show originals:references/simples/<caminho-do-arquivo>

# 3. Integrar em development e promover para staging
git checkout development
git merge --no-ff feature/simples-calculo-ibs-cbs
git checkout staging
git merge --no-ff development
docker compose up --build -d

# 4. Promover para main após homologação
git checkout main
git merge --no-ff staging
git tag -a v0.1.0 -m "Release v0.1.0"
```


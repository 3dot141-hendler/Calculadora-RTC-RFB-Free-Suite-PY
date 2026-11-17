# Calculadora RTC RFB Free Suite PY

Ecossistema open-source unificado em **Python (FastAPI)**, **Docker** e **Bootstrap 5.3** para substituir e unificar as calculadoras oficiais da Reforma Tributária (RTC) da Receita Federal:

1. **Simples Nacional** (`/api/v1/simples`) — Ref.: `ReceitaFederal/calculadora-rtc-simples-nacional`
2. **Regime Regular** (`/api/v1/regime-regular`) — Ref.: `ReceitaFederal/calculadora-rtc-regime-regular`
3. **Gerador DANFSE** (`/api/v1/danfse`) — Ref.: `ReceitaFederal/calculadora-rtc-gerador-danfse`

## Estrutura do Monorepo

- `references/` — Códigos originais da RFB mantidos na branch `originals` apenas para consulta.
- `backend/` — API modular FastAPI com validação estrita em Pydantic e testes Pytest.
- `frontend/` — Interface web HTML5 semântica, Bootstrap 5.3, carregamento modular de partials, cache-busting dinâmico (`?v={mtime}`) e sidebar flexível com modo mini.
- `scripts/` e `docs/` — Automação e documentação do Git Flow (`originals`, `development`, `staging`, `main`).
- `docker-compose.yml` — Orquestração integrada (Backend FastAPI + Frontend Nginx) para homologação na branch `staging`.

## Execução Local (Desenvolvimento)

```powershell
.venv\Scripts\pip.exe install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\pytest.exe
..\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Acesse: `http://localhost:8000` (Frontend) e `http://localhost:8000/api/docs` (Swagger).

## Homologação com Docker Compose (Staging)

```bash
docker compose up --build -d
```

Acesse: `http://localhost:8080` (Frontend + Proxy `/api/`) e `http://localhost:8000/api/v1/health`.


# Calculadora RTC RFB Free Suite PY

Ecossistema open-source unificado em **Python (FastAPI)**, **Docker** e **Bootstrap 5.3** para substituir e unificar as calculadoras oficiais da Reforma Tributária (RTC) da Receita Federal:

1. **Comparador Tributário** (`/api/v1/comparador`) — Simulação lado a lado entre Simples Nacional (DAS), Simples Híbrido e Regime Regular com impacto B2B, **Fator R (Anexo III vs. V)**, comparador **Lucro Presumido vs. Lucro Real** e relatório executivo imprimível em 1 página A4.
2. **Simples Nacional** (`/api/v1/simples`) — Ref.: `ReceitaFederal/calculadora-rtc-simples-nacional` (LC 123/2006 Anexos I–V, NT 2026.005, operação multi-itens em lote e observabilidade `VSN-*`).
3. **Regime Regular** (`/api/v1/regime-regular`) — Ref.: `ReceitaFederal/calculadora-rtc-regime-regular` (IBS/CBS/IS, crédito presumido, redução de base, compra governamental, motor seguro AST `ADR001` e Bases Unificadas NF-e/NFC-e e NFS-e/Locação 99.03).
4. **Gerador DANFSe v2.0** (`/api/v1/danfse`) — Ref.: `ReceitaFederal/calculadora-rtc-gerador-danfse` (Parser XML seguro XXE com blocos `IBSCBS`, `interm` e `subst`, PDF binário nativo em ReportLab + QR Code vetorial NT 008).
5. **Tabelas Oficiais** (`/api/v1/tabelas`) — Catálogo SQLite somente-leitura (`27 UFs`, `164 CST/cClassTrib`, `15 cAtivSN`, `334 NCM IS`, `118 NBS`, `43 Tratamentos ADR001`, tabelas V0019 e `5.525 municípios IBGE`).

## Estrutura do Monorepo

- `references/` — Códigos originais da RFB mantidos na branch `originals` apenas para consulta.
- `backend/` — API modular FastAPI com validação estrita em Pydantic, arredondamento `HALF_EVEN` e suíte Pytest (`79 passed`).
- `frontend/` — Interface web HTML5 semântica, Bootstrap 5.3, carregamento modular de partials, cache-busting dinâmico (`?v={mtime}`), formatação PT-BR e sidebar flexível com modo mini.
- `scripts/` e `docs/` — Sincronização automatizada do SQLite (`scripts/sync_rfb_sqlite.py`) e documentação do Git Flow (`originals`, `development`, `staging`, `main`).
- `docker-compose.yml` — Orquestração integrada (Backend FastAPI + Frontend Nginx) para homologação na branch `staging`.

## Execução Local (Desenvolvimento)

```powershell
.venv\Scripts\pip.exe install -r backend\requirements-dev.txt
.venv\Scripts\python.exe -m pytest backend\tests -q
.venv\Scripts\uvicorn.exe --app-dir backend app.main:app --reload
```

Acesse:
- `http://localhost:8000` (Interface Web + Comparador + Exemplos Interativos da API)
- `http://localhost:8000/api/docs` (Swagger UI)

## Exemplos Rápidos de Consumo da API

Exemplo chamando o **Comparador Tributário** (`POST /api/v1/comparador/simular`). Outros endpoints e teste ao vivo estão disponíveis na aba **Exemplos API** da interface web.

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/comparador/simular" \
  -H "Content-Type: application/json" \
  -d '{
    "receita_bruta_12m": "720000.00",
    "valor_operacao": "50000.00",
    "anexo": "I",
    "uf": "RS",
    "c_class_trib": "000001",
    "creditos_anteriores": "4500.00",
    "percentual_vendas_b2b": "100.00"
  }'
```

### Python (`requests`)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/comparador/simular",
    json={
        "receita_bruta_12m": "720000.00",
        "valor_operacao": "50000.00",
        "anexo": "I",
        "uf": "RS",
        "c_class_trib": "000001",
        "creditos_anteriores": "4500.00",
        "percentual_vendas_b2b": "100.00",
    },
    timeout=10,
)
response.raise_for_status()
print(response.json())
```

### JavaScript / Node.js (`fetch`)

```javascript
const response = await fetch("http://localhost:8000/api/v1/comparador/simular", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    receita_bruta_12m: "720000.00",
    valor_operacao: "50000.00",
    anexo: "I",
    uf: "RS",
    c_class_trib: "000001",
    creditos_anteriores: "4500.00",
    percentual_vendas_b2b: "100.00",
  }),
});
const data = await response.json();
console.log(data);
```

### PHP (`cURL`)

```php
<?php
$payload = json_encode([
    "receita_bruta_12m" => "720000.00",
    "valor_operacao" => "50000.00",
    "anexo" => "I",
    "uf" => "RS",
    "c_class_trib" => "000001",
    "creditos_anteriores" => "4500.00",
    "percentual_vendas_b2b" => "100.00",
]);

$ch = curl_init("http://localhost:8000/api/v1/comparador/simular");
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ["Content-Type: application/json"],
    CURLOPT_POSTFIELDS => $payload,
]);
$response = curl_exec($ch);
curl_close($ch);
print_r(json_decode($response, true));
```

## Homologação com Docker Compose (Staging)

```bash
docker compose up --build -d
```

Acesse: `http://localhost:8080` (Frontend + Proxy `/api/`) e `http://localhost:8000/api/v1/health`.
